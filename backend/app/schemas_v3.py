from pydantic import BaseModel, Field
from typing import Literal

class QuestionItem(BaseModel):
    """A single normalized question from any questionnaire format."""
    question_id: str                        # e.g., "SIG_A.1.1" or "CAIQ_AIS-01" or "Q42"
    domain: str = ""                        # e.g., "Access Control", "Encryption", "Business Resiliency"
    question_text: str
    response_type: Literal["boolean", "narrative", "multiple_choice", "evidence_upload"] = "narrative"
    options: list[str] = []                 # For multiple_choice
    framework: str = ""                     # "sig_core", "sig_lite", "caiq", "custom"

class KBDocument(BaseModel):
    """A security policy or evidence document in the knowledge base."""
    filename: str
    doc_type: Literal["soc2_report", "pentest_summary", "incident_response_plan",
                       "security_policy", "prior_questionnaire", "architecture_doc", "other"]
    description: str = ""

class RetrievedEvidence(BaseModel):
    """A chunk retrieved from the KB matching a specific question."""
    text: str
    source_filename: str
    page_number: int = 0
    similarity_score: float

class DraftResponse(BaseModel):
    """A generated response for a single question."""
    question_id: str
    question_text: str
    domain: str
    response_text: str
    response_type: Literal["boolean", "narrative", "multiple_choice"] = "narrative"
    boolean_value: bool | None = None       # For boolean questions
    citations: list[str]                    # Source tags
    confidence: float = Field(ge=0, le=1)
    status: Literal["auto_approved", "needs_review", "human_overridden"] = "needs_review"
    reviewer_notes: str = ""

class ComplianceConfig(BaseModel):
    """User configuration for questionnaire processing."""
    confidence_threshold: float = Field(default=0.8, ge=0, le=1)
    auto_approve_above: float = Field(default=0.9, ge=0, le=1)
    company_name: str = "Tracelight"
    default_tone: Literal["formal", "concise", "technical"] = "formal"

class ComplianceGenerateRequest(BaseModel):
    """Request body for POST /api/v3/compliance/generate."""
    kb_session_id: str                      # From prior upload-kb call
    questionnaire_session_id: str           # From prior upload-questionnaire call
    config: ComplianceConfig = ComplianceConfig()

class ComplianceGenerateResponse(BaseModel):
    job_id: str
    status: Literal["processing", "completed", "failed"]
    total_questions: int = 0
    auto_approved: int = 0
    needs_review: int = 0
    responses: list[DraftResponse] | None = None
    download_urls: dict[str, str] = {}
    generated_at: str

class ReviewUpdate(BaseModel):
    """PATCH body for human review of a single question."""
    response_text: str | None = None        # Override the generated response
    boolean_value: bool | None = None
    status: Literal["auto_approved", "human_overridden"] = "human_overridden"
    reviewer_notes: str = ""
