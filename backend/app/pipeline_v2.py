import time
import uuid
try:
    import chromadb
except ImportError:
    chromadb = None
from app.schemas_v2 import MemoGenerateRequest, MemoSection
from app.agents.quant_extractor import QuantExtractor
from app.agents.narrative_drafter import NarrativeDrafter
from app.agents.citation_formatter import CitationFormatter
from app.database import update_job
from app.logging_config import get_logger

log = get_logger("pipeline_v2")

# Keep a single client in memory
chroma_client = chromadb.EphemeralClient() if chromadb else None

def get_chroma_client():
    return chroma_client

async def run_memo_pipeline(job_id: str, request: MemoGenerateRequest, settings):
    start_time = time.perf_counter()
    log.info("pipeline_started", job_id=job_id, phase="v2")
    try:
        await update_job(job_id, "processing")
        
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
            sec_start = time.perf_counter()
            sec = drafter.draft_section(request.session_id, sec_id, title, metrics, request.config)
            log.info("section_drafted", job_id=job_id, section=sec_id, duration_ms=(time.perf_counter() - sec_start) * 1000)
            sections.append(sec)
        
        formatter = CitationFormatter("app/templates_v2", settings.output_dir)
        urls = formatter.format_deliverables(job_id, sections, metrics)
        
        result_data = {
            "sections": [s.model_dump() for s in sections],
            "urls": urls
        }
        await update_job(job_id, "completed", result_data)
        log.info("pipeline_completed", job_id=job_id, phase="v2", status="completed", total_duration_ms=(time.perf_counter() - start_time) * 1000)
    except Exception as e:
        await update_job(job_id, "failed", error=str(e))
        log.error("pipeline_failed", job_id=job_id, phase="v2", error=str(e), exc_info=True)
