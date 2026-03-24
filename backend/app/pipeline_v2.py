import uuid
import datetime
import chromadb
from app.schemas_v2 import MemoGenerateRequest, MemoSection
from app.agents.quant_extractor import QuantExtractor
from app.agents.narrative_drafter import NarrativeDrafter
from app.agents.citation_formatter import CitationFormatter

JOB_STATUS = {}
JOB_RESULTS = {}

# Keep a single client in memory
chroma_client = chromadb.EphemeralClient()

def get_chroma_client():
    return chroma_client

async def run_memo_pipeline(job_id: str, request: MemoGenerateRequest, settings):
    try:
        JOB_STATUS[job_id] = "processing"
        
        quant_ext = QuantExtractor(settings.output_dir)
        metrics = request.financial_data_inline
        if not metrics and request.financial_data_job_id:
            metrics = quant_ext.extract_from_job(request.financial_data_job_id)
        
        if not metrics:
            raise ValueError("No financial metrics provided")

        drafter = NarrativeDrafter(chroma_client, settings)
        
        sections = []
        for sec_id in request.config.sections:
            title = sec_id.replace("_", " ").title()
            sec = drafter.draft_section(request.session_id, sec_id, title, metrics, request.config)
            sections.append(sec)
        
        JOB_RESULTS[job_id] = sections
        
        formatter = CitationFormatter("app/templates_v2", settings.output_dir)
        urls = formatter.format_deliverables(job_id, sections, metrics)
        
        JOB_STATUS[job_id] = "completed"
        JOB_RESULTS[job_id + "_urls"] = urls
    except Exception as e:
        JOB_STATUS[job_id] = "failed"
        JOB_RESULTS[job_id + "_error"] = str(e)
