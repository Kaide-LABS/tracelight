import re
import httpx
from jinja2 import Environment, FileSystemLoader
from app.schemas_v2 import MemoSection, CitedMetrics, MemoConfig
from app.config import Settings
from sentence_transformers import SentenceTransformer
import tenacity
from app.logging_config import get_logger

log = get_logger("narrative_drafter")

embed_model = SentenceTransformer('all-MiniLM-L6-v2')


class NarrativeDrafter:
    def __init__(self, chroma_client, settings: Settings):
        self.settings = settings
        self.jinja_env = Environment(loader=FileSystemLoader("app/prompts"))
        self.chroma_client = chroma_client

        # Initialize LLM client based on provider
        if settings.llm_provider == "google":
            from google import genai
            self.google_client = genai.Client(api_key=settings.llm_api_key)
            self.openai_client = None
        else:
            self.google_client = None

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_exponential(min=1, max=5),
        retry=tenacity.retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=lambda retry_state: log.warning("llm_retry", attempt=retry_state.attempt_number),
    )
    def _call_llm(self, prompt: str) -> str:
        """Dual-provider LLM call — mirrors profiler agent pattern."""
        if self.settings.llm_provider == "google":
            response = self.google_client.models.generate_content(
                model=self.settings.llm_model,  # "gemini-3.1-pro-preview"
                contents=prompt,
                config={"temperature": 0.2},
            )
            return response.text
        else:
            # OpenAI via httpx (sync for BackgroundTasks context)
            resp = httpx.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_model,  # "gpt-5.2-chat-latest"
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
                timeout=60.0,
            )
            return resp.json()["choices"][0]["message"]["content"]

    def draft_section(self, session_id: str, section_id: str, title: str, metrics: CitedMetrics, config: MemoConfig) -> MemoSection:
        collection_name = f"session_{session_id}"
        retrieved_chunks = []
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            query_embedding = embed_model.encode([f"{title} for {config.firm_name}"]).tolist()
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=5
            )
            if results and results["documents"] and results["documents"][0]:
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    retrieved_chunks.append({
                        "text": doc,
                        "metadata": meta
                    })
        except Exception:
            pass

        if section_id == "executive_summary":
            template = self.jinja_env.get_template("executive_summary.j2")
            prompt = template.render(
                company_name=metrics.company_name,
                deal_type=metrics.deal_type,
                firm_name=config.firm_name,
                key_metrics=metrics.metrics[:5],
                section_summaries=[]
            )
        else:
            template = self.jinja_env.get_template("memo_section.j2")
            prompt = template.render(
                section_title=title,
                relevant_metrics=metrics.metrics,
                retrieved_chunks=retrieved_chunks,
                target_words=300
            )

        content = self._call_llm(prompt)

        # Post-generation citation validation
        citations_raw = re.findall(r'\[(.*?)\]', content)
        valid_tags = {m.source_tag for m in metrics.metrics}

        # Also build valid tags from retrieved chunks
        for chunk in retrieved_chunks:
            meta = chunk["metadata"]
            valid_tags.add(f"{meta['source_filename']}:page_{meta['page_number']}")

        # Filter to only genuine source_tags — must exist in valid_tags
        verified_citations = [c for c in citations_raw if c in valid_tags]

        # Confidence = ratio of verified citations to total bracketed references
        # Exclude known non-citation brackets (e.g., "INSUFFICIENT DATA")
        claim_citations = [c for c in citations_raw if c != "INSUFFICIENT DATA — REQUIRES ANALYST INPUT"]
        total_claims = len(claim_citations)
        cited_claims = len(verified_citations)

        confidence = cited_claims / total_claims if total_claims > 0 else 1.0
        if "INSUFFICIENT DATA" in content:
            confidence = min(confidence, 0.3)

        needs_review = confidence < config.confidence_threshold

        return MemoSection(
            section_id=section_id,
            title=title,
            content=content,
            citations=verified_citations,
            confidence=round(confidence, 2),
            needs_review=needs_review
        )
