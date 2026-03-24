from pydantic import BaseModel, Field
from typing import Literal

class SourceDocument(BaseModel):
    """A qualitative source document uploaded by the user."""
    filename: str
    doc_type: Literal["cim", "management_presentation", "expert_call", "market_report", "other"]
    description: str = ""

class FinancialMetric(BaseModel):
    """A single extracted metric with mandatory source attribution."""
    name: str                               # e.g. "base_case_irr"
    value: float | str
    unit: str = ""                          # e.g. "%", "$M", "x"
    scenario: Literal["base", "upside", "downside"] = "base"
    source_tag: str                         # e.g. "model_export:row_42:irr" or "cim:page_12"

class CitedMetrics(BaseModel):
    """All extracted financial metrics, each source-tagged."""
    company_name: str
    deal_type: str                          # e.g. "LBO", "Growth Equity", "M&A"
    currency: str = "USD"
    metrics: list[FinancialMetric]

class MemoSection(BaseModel):
    """One section of the IC memo."""
    section_id: str                         # e.g. "executive_summary", "investment_thesis"
    title: str
    content: str                            # Markdown with inline citations [source_tag]
    citations: list[str]                    # List of source_tags referenced
    confidence: float = Field(ge=0, le=1)   # LLM's confidence in the section
    needs_review: bool = False              # Flagged if confidence < threshold

class MemoConfig(BaseModel):
    """User configuration for memo generation."""
    memo_type: Literal["ic_memo", "exec_deck", "both"] = "both"
    firm_name: str = ""
    sections: list[str] = Field(default_factory=lambda: [
        "executive_summary",
        "investment_thesis",
        "market_analysis",
        "financial_projections",
        "deal_structure",
        "risk_mitigation",
    ])
    tone: Literal["formal", "concise", "technical"] = "formal"
    max_pages: int = Field(default=30, ge=5, le=50)
    confidence_threshold: float = Field(default=0.7, ge=0, le=1)

class MemoGenerateRequest(BaseModel):
    """Request body for POST /api/v2/memo/generate."""
    session_id: str                         # From prior upload-sources call
    financial_data_job_id: str | None = None # Optional: pull from Phase 1 output
    financial_data_inline: CitedMetrics | None = None  # Or provide directly
    config: MemoConfig = MemoConfig()

class MemoGenerateResponse(BaseModel):
    job_id: str
    status: Literal["processing", "completed", "failed"]
    sections: list[MemoSection] | None = None
    download_urls: dict[str, str] = {}      # {"docx": "/api/v2/memo/download/xxx?fmt=docx", ...}
    audit_trail_url: str | None = None
    generated_at: str
