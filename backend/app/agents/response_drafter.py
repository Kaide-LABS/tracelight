import re
import httpx
from jinja2 import Environment, FileSystemLoader
from typing import List
from app.schemas_v3 import QuestionItem, DraftResponse, RetrievedEvidence, ComplianceConfig
from app.config import Settings
import tenacity
from app.logging_config import get_logger

log = get_logger("response_drafter")

class ResponseDrafterAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jinja_env = Environment(loader=FileSystemLoader("app/prompts"))

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
        """Dual-provider LLM call."""
        if self.settings.llm_provider == "google":
            response = self.google_client.models.generate_content(
                model=self.settings.llm_model,
                contents=prompt,
                config={"temperature": 0.2},
            )
            return response.text
        else:
            resp = httpx.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
                timeout=60.0,
            )
            return resp.json()["choices"][0]["message"]["content"]

    def draft_response(self, question: QuestionItem, evidence: List[dict], config: ComplianceConfig) -> DraftResponse:
        template = self.jinja_env.get_template("compliance_response.j2")
        prompt = template.render(
            company_name=config.company_name,
            tone=config.default_tone,
            question_id=question.question_id,
            domain=question.domain,
            question_text=question.question_text,
            response_type=question.response_type,
            options=question.options,
            retrieved_evidence=evidence
        )

        content = self._call_llm(prompt)

        # Citation validation
        citations_raw = re.findall(r'\[(.*?)\]', content)
        
        valid_tags = set()
        for chunk in evidence:
            valid_tags.add(f"{chunk['source_filename']}:page_{chunk['page_number']}")

        verified_citations = [c for c in citations_raw if c in valid_tags]
        claim_citations = [c for c in citations_raw if "REQUIRES REVIEW" not in c and "INSUFFICIENT KB" not in c]

        total_claims = len(claim_citations)
        cited_claims = len(verified_citations)

        citation_score = cited_claims / total_claims if total_claims > 0 else 1.0
        
        max_sim = max([e.get("similarity_score", 0.0) for e in evidence]) if evidence else 0.0
        confidence = citation_score * max_sim
        
        if "REQUIRES REVIEW" in content:
            confidence = min(confidence, 0.3)

        # For boolean questions, extract true/false
        boolean_value = None
        if question.response_type == "boolean":
            match = re.search(r'\b(Yes|No)\b', content, re.IGNORECASE)
            if match:
                boolean_value = match.group(1).lower() == "yes"

        return DraftResponse(
            question_id=question.question_id,
            question_text=question.question_text,
            domain=question.domain,
            response_text=content,
            response_type=question.response_type,
            boolean_value=boolean_value,
            citations=verified_citations,
            confidence=round(confidence, 2)
        )
