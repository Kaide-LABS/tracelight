import os
import re
from google import genai
from jinja2 import Environment, FileSystemLoader
from app.schemas_v2 import MemoSection, CitedMetrics, MemoConfig
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

class NarrativeDrafter:
    def __init__(self, chroma_client):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")
        self.client = genai.Client(api_key=api_key)
        self.jinja_env = Environment(loader=FileSystemLoader("app/prompts"))
        self.chroma_client = chroma_client

    def draft_section(self, session_id: str, section_id: str, title: str, metrics: CitedMetrics, config: MemoConfig) -> MemoSection:
        collection_name = f"session_{session_id}"
        retrieved_chunks = []
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            # Embed query
            query_embedding = model.encode([f"{title} for {config.firm_name}"]).tolist()
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
        except Exception as e:
            # Collection might not exist if no docs uploaded
            pass

        if section_id == "executive_summary":
            template = self.jinja_env.get_template("executive_summary.j2")
            prompt = template.render(
                company_name=metrics.company_name,
                deal_type=metrics.deal_type,
                firm_name=config.firm_name,
                key_metrics=metrics.metrics[:5],
                section_summaries=[] # For a full implementation, you'd pass summaries of other sections
            )
        else:
            template = self.jinja_env.get_template("memo_section.j2")
            prompt = template.render(
                section_title=title,
                relevant_metrics=metrics.metrics,
                retrieved_chunks=retrieved_chunks,
                target_words=300
            )

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        content = response.text

        # Post-generation validation
        citations = re.findall(r'\[(.*?)\]', content)
        valid_tags = {m.source_tag for m in metrics.metrics}
        if retrieved_chunks:
             # In a real impl, chunks might have specific tags. Here we just assume anything with brackets might be a citation
             pass
        
        # Calculate confidence
        total_claims = len(citations)
        cited_claims = len([c for c in citations if c in valid_tags or ":" in c]) # Basic check
        
        confidence = cited_claims / total_claims if total_claims > 0 else 1.0
        if "INSUFFICIENT DATA" in content:
            confidence = 0.0
            
        needs_review = confidence < config.confidence_threshold

        return MemoSection(
            section_id=section_id,
            title=title,
            content=content,
            citations=citations,
            confidence=confidence,
            needs_review=needs_review
        )
