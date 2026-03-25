import asyncio
import time
import uuid
import datetime
import traceback
from typing import Dict, Any, List
from fastapi import BackgroundTasks
try:
    import chromadb
except ImportError:
    chromadb = None
from app.config import Settings
from app.schemas_v3 import (
    ComplianceGenerateRequest, ComplianceGenerateResponse, 
    DraftResponse, ComplianceConfig, QuestionItem
)
from app.agents.kb_retriever import KBRetrieverAgent
from app.agents.response_drafter import ResponseDrafterAgent
from app.agents.routing_exporter import RoutingExporterAgent
from app.database import create_job, update_job, get_job
from app.logging_config import get_logger

log = get_logger("pipeline_v3")

# In-memory session store for parsed questionnaires
questionnaires_db: Dict[str, List[QuestionItem]] = {}

def get_chroma_client(settings: Settings):
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

async def run_compliance_pipeline(
    job_id: str, 
    request: ComplianceGenerateRequest, 
    settings: Settings
):
    start_time = time.perf_counter()
    log.info("pipeline_started", job_id=job_id, phase="v3")
    try:
        # Retrieve parsed questionnaire
        questions = questionnaires_db.get(request.questionnaire_session_id)
        if not questions:
            raise ValueError("Questionnaire session not found")

        total_questions = len(questions)
        responses = []

        # Update initial job state with total_questions
        current_job = await get_job(job_id)
        result_data = current_job.get("result") or {}
        result_data.update({
            "total_questions": total_questions,
            "auto_approved": 0,
            "needs_review": 0,
            "responses": [],
            "download_urls": {}
        })
        await update_job(job_id, "processing", result_data)
        
        # Initialize Agents
        chroma_client = get_chroma_client(settings)
        retriever = KBRetrieverAgent(chroma_client)
        drafter = ResponseDrafterAgent(settings)
        exporter = RoutingExporterAgent(settings.output_dir)

        # Process each question sequentially for safety, but could be parallelized
        for i, q in enumerate(questions):
            q_start = time.perf_counter()
            # 1. Retrieve evidence
            evidence = retriever.retrieve_for_question(q.question_text, top_k=5)
            
            # 2. Draft response
            draft = await asyncio.to_thread(
                drafter.draft_response, 
                question=q, 
                evidence=evidence, 
                config=request.config
            )
            
            # 3. Apply routing logic
            if draft.confidence >= request.config.auto_approve_above:
                draft.status = "auto_approved"
            elif draft.confidence < request.config.confidence_threshold:
                draft.status = "needs_review"
            else:
                draft.status = "needs_review"  # Conservative

            responses.append(draft)
            log.info("question_processed", job_id=job_id, question_id=q.question_id, duration_ms=(time.perf_counter() - q_start) * 1000)
            
            # Update job progress in database
            result_data["responses"] = [r.model_dump() for r in responses]
            await update_job(job_id, "processing", result_data)
            
        # Tally metrics
        auto_approved = sum(1 for r in responses if r.status == "auto_approved")
        needs_review = sum(1 for r in responses if r.status == "needs_review")
        
        result_data["auto_approved"] = auto_approved
        result_data["needs_review"] = needs_review
        
        # Export (initial, though might change after review)
        csv_path = exporter.export_csv(job_id, responses)
        docx_path = exporter.export_docx(job_id, responses)
        json_path = exporter.export_json(job_id, responses)
        
        result_data["download_urls"] = {
            "csv": f"/api/v3/compliance/download/{job_id}?fmt=csv",
            "docx": f"/api/v3/compliance/download/{job_id}?fmt=docx",
            "json": f"/api/v3/compliance/download/{job_id}?fmt=json",
        }
        
        await update_job(job_id, "completed", result_data)
        log.info("pipeline_completed", job_id=job_id, phase="v3", status="completed", total_duration_ms=(time.perf_counter() - start_time) * 1000)

    except Exception as e:
        log.error("pipeline_failed", job_id=job_id, phase="v3", error=str(e), exc_info=True)
        await update_job(job_id, "failed", error=str(e))

async def start_compliance_job(request: ComplianceGenerateRequest, background_tasks: BackgroundTasks, settings: Settings) -> str:
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    initial_result = {
        "job_id": job_id,
        "total_questions": 0,
        "auto_approved": 0,
        "needs_review": 0,
        "responses": [],
        "download_urls": {},
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    await create_job(job_id, "v3", request.model_dump())
    await update_job(job_id, "pending", initial_result)
    background_tasks.add_task(run_compliance_pipeline, job_id, request, settings)
    return job_id

async def get_job_status(job_id: str) -> ComplianceGenerateResponse:
    job = await get_job(job_id)
    if not job:
        raise KeyError(f"Job {job_id} not found")
    
    data = job.get("result", {})
    return ComplianceGenerateResponse(
        job_id=job_id,
        status=job["status"],
        total_questions=data.get("total_questions", 0),
        auto_approved=data.get("auto_approved", 0),
        needs_review=data.get("needs_review", 0),
        responses=data.get("responses", []),
        download_urls=data.get("download_urls", {}),
        generated_at=data.get("generated_at", job.get("updated_at", ""))
    )
    
async def update_job_response(job_id: str, question_id: str, updates: dict):
    job = await get_job(job_id)
    if not job:
        raise KeyError(f"Job {job_id} not found")
    
    result_data = job.get("result", {})
    responses = result_data.get("responses", [])
    
    found = False
    for r in responses:
        if r.get("question_id") == question_id:
            found = True
            if "response_text" in updates and updates["response_text"] is not None:
                r["response_text"] = updates["response_text"]
            if "boolean_value" in updates and updates["boolean_value"] is not None:
                r["boolean_value"] = updates["boolean_value"]
            if "status" in updates and updates["status"] is not None:
                old_status = r.get("status")
                r["status"] = updates["status"]
                
                # update tallies
                if old_status == "auto_approved" and r["status"] != "auto_approved":
                    result_data["auto_approved"] = max(0, result_data.get("auto_approved", 0) - 1)
                elif old_status == "needs_review" and r["status"] != "needs_review":
                    result_data["needs_review"] = max(0, result_data.get("needs_review", 0) - 1)
                    
                if r["status"] == "auto_approved" and old_status != "auto_approved":
                    result_data["auto_approved"] = result_data.get("auto_approved", 0) + 1
                elif r["status"] == "needs_review" and old_status != "needs_review":
                    result_data["needs_review"] = result_data.get("needs_review", 0) + 1
                    
            if "reviewer_notes" in updates and updates["reviewer_notes"] is not None:
                r["reviewer_notes"] = updates["reviewer_notes"]
            break
            
    if found:
        result_data["responses"] = responses
        await update_job(job_id, job["status"], result_data)
        return True
    return False

async def regenerate_exports(job_id: str, settings: Settings):
    job = await get_job(job_id)
    if not job:
        raise KeyError(f"Job {job_id} not found")
        
    exporter = RoutingExporterAgent(settings.output_dir)
    result_data = job.get("result", {})
    responses_data = result_data.get("responses", [])
    
    # We need to convert dicts back to DraftResponse objects for the exporter
    responses = [DraftResponse(**r) for r in responses_data]
    
    exporter.export_csv(job_id, responses)
    exporter.export_docx(job_id, responses)
    exporter.export_json(job_id, responses)
