import asyncio
import uuid
import datetime
import traceback
from typing import Dict, Any, List
from fastapi import BackgroundTasks
import chromadb
from app.config import Settings
from app.schemas_v3 import (
    ComplianceGenerateRequest, ComplianceGenerateResponse, 
    DraftResponse, ComplianceConfig, QuestionItem
)
from app.agents.kb_retriever import KBRetrieverAgent
from app.agents.response_drafter import ResponseDrafterAgent
from app.agents.routing_exporter import RoutingExporterAgent

# In-memory job tracker
jobs_db: Dict[str, Dict[str, Any]] = {}

# In-memory session store for parsed questionnaires
questionnaires_db: Dict[str, List[QuestionItem]] = {}

def get_chroma_client(settings: Settings):
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

async def run_compliance_pipeline(
    job_id: str, 
    request: ComplianceGenerateRequest, 
    settings: Settings
):
    try:
        jobs_db[job_id]["status"] = "processing"
        
        # Initialize Agents
        chroma_client = get_chroma_client(settings)
        retriever = KBRetrieverAgent(chroma_client)
        drafter = ResponseDrafterAgent(settings)
        exporter = RoutingExporterAgent(settings.output_dir)

        # Retrieve parsed questionnaire
        questions = questionnaires_db.get(request.questionnaire_session_id)
        if not questions:
            raise ValueError("Questionnaire session not found")

        jobs_db[job_id]["total_questions"] = len(questions)
        responses = []

        # Process each question sequentially for safety, but could be parallelized
        for i, q in enumerate(questions):
            # 1. Retrieve evidence
            evidence = retriever.retrieve_for_question(q.question_text, top_k=5)
            
            # 2. Draft response
            # we need to await a sync wrapper or run in executor if _call_llm is synchronous 
            # (since we used sync httpx or sync gemini). Let's wrap in asyncio.to_thread
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
            
            # Update job progress
            jobs_db[job_id]["responses"] = responses
            
        # Tally metrics
        auto_approved = sum(1 for r in responses if r.status == "auto_approved")
        needs_review = sum(1 for r in responses if r.status == "needs_review")
        
        jobs_db[job_id]["auto_approved"] = auto_approved
        jobs_db[job_id]["needs_review"] = needs_review
        
        # Export (initial, though might change after review)
        csv_path = exporter.export_csv(job_id, responses)
        docx_path = exporter.export_docx(job_id, responses)
        json_path = exporter.export_json(job_id, responses)
        
        jobs_db[job_id]["download_urls"] = {
            "csv": f"/api/v3/compliance/download/{job_id}?fmt=csv",
            "docx": f"/api/v3/compliance/download/{job_id}?fmt=docx",
            "json": f"/api/v3/compliance/download/{job_id}?fmt=json",
        }
        
        jobs_db[job_id]["status"] = "completed"

    except Exception as e:
        traceback.print_exc()
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)

def start_compliance_job(request: ComplianceGenerateRequest, background_tasks: BackgroundTasks, settings: Settings) -> str:
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "total_questions": 0,
        "auto_approved": 0,
        "needs_review": 0,
        "responses": [],
        "download_urls": {},
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    background_tasks.add_task(run_compliance_pipeline, job_id, request, settings)
    return job_id

def get_job_status(job_id: str) -> ComplianceGenerateResponse:
    if job_id not in jobs_db:
        raise KeyError(f"Job {job_id} not found")
    
    data = jobs_db[job_id]
    return ComplianceGenerateResponse(
        job_id=job_id,
        status=data["status"],
        total_questions=data["total_questions"],
        auto_approved=data["auto_approved"],
        needs_review=data["needs_review"],
        responses=data["responses"],
        download_urls=data.get("download_urls", {}),
        generated_at=data["generated_at"]
    )
    
def update_job_response(job_id: str, question_id: str, updates: dict):
    if job_id not in jobs_db:
        raise KeyError(f"Job {job_id} not found")
    
    job = jobs_db[job_id]
    for r in job["responses"]:
        if r.question_id == question_id:
            if "response_text" in updates and updates["response_text"] is not None:
                r.response_text = updates["response_text"]
            if "boolean_value" in updates and updates["boolean_value"] is not None:
                r.boolean_value = updates["boolean_value"]
            if "status" in updates and updates["status"] is not None:
                old_status = r.status
                r.status = updates["status"]
                
                # update tallies
                if old_status == "auto_approved" and r.status != "auto_approved":
                    job["auto_approved"] -= 1
                elif old_status == "needs_review" and r.status != "needs_review":
                    job["needs_review"] -= 1
                    
                if r.status == "auto_approved":
                    job["auto_approved"] += 1
                elif r.status == "needs_review":
                    job["needs_review"] += 1
                    
            if "reviewer_notes" in updates and updates["reviewer_notes"] is not None:
                r.reviewer_notes = updates["reviewer_notes"]
            return True
            
    return False

def regenerate_exports(job_id: str, settings: Settings):
    if job_id not in jobs_db:
        raise KeyError(f"Job {job_id} not found")
        
    exporter = RoutingExporterAgent(settings.output_dir)
    job = jobs_db[job_id]
    exporter.export_csv(job_id, job["responses"])
    exporter.export_docx(job_id, job["responses"])
    exporter.export_json(job_id, job["responses"])
