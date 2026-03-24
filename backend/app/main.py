import os
import uuid
from fastapi import FastAPI, Depends, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import GenerateRequest, GenerateResponse
from app.config import Settings
from app.pipeline import run_pipeline
from app.templates import PRESETS

# Phase 2 imports
from app.schemas_v2 import MemoGenerateRequest, MemoGenerateResponse
from app.pipeline_v2 import run_memo_pipeline, JOB_STATUS, JOB_RESULTS, get_chroma_client
from app.agents.context_harvester import ContextHarvester

app = FastAPI(title="Tracelight Synthetic Data Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_settings():
    return Settings()

@app.on_event("startup")
async def startup_event():
    settings = get_settings()
    os.makedirs(settings.output_dir, exist_ok=True)
    os.makedirs("app/templates_v2", exist_ok=True)
    
    # Generate default templates if missing
    import docx
    from pptx import Presentation
    
    docx_path = "app/templates_v2/ic_memo_template.docx"
    if not os.path.exists(docx_path):
        doc = docx.Document()
        doc.add_heading('Investment Committee Memorandum', 0)
        for sec in ['executive_summary', 'investment_thesis', 'market_analysis', 'financial_projections', 'deal_structure', 'risk_mitigation']:
            doc.add_heading(sec.replace("_", " ").title(), level=1)
            doc.add_paragraph(f"{{{{ {sec} }}}}")
        doc.save(docx_path)
        
    pptx_path = "app/templates_v2/exec_deck_template.pptx"
    if not os.path.exists(pptx_path):
        prs = Presentation()
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = "Executive Deck Template"
        subtitle.text = "Tracelight Generated"
        prs.save(pptx_path)

@app.post("/api/v1/generate", response_model=GenerateResponse)
async def generate_data(request: GenerateRequest, settings: Settings = Depends(get_settings)):
    return await run_pipeline(request, settings)

@app.get("/api/v1/download/{job_id}")
async def download_data(job_id: str, settings: Settings = Depends(get_settings)):
    csv_path = f"{settings.output_dir}/{job_id}.csv"
    json_path = f"{settings.output_dir}/{job_id}.json"
    
    if os.path.exists(csv_path):
        return FileResponse(csv_path, media_type="text/csv", filename=f"{job_id}.csv")
    elif os.path.exists(json_path):
        return FileResponse(json_path, media_type="application/json", filename=f"{job_id}.json")
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/v1/templates")
async def get_templates():
    return PRESETS

# ======================= PHASE 2 ROUTES =======================

@app.post("/api/v2/memo/upload-sources")
async def upload_sources(files: list[UploadFile] = File(...)):
    session_id = str(uuid.uuid4())
    harvester = ContextHarvester(get_chroma_client())
    
    temp_dir = f"/tmp/{session_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        for file in files:
            filepath = os.path.join(temp_dir, file.filename)
            with open(filepath, "wb") as f:
                f.write(await file.read())
            harvester.process_file(filepath, session_id)
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    return {"session_id": session_id}

@app.post("/api/v2/memo/generate", response_model=MemoGenerateResponse)
async def generate_memo(request: MemoGenerateRequest, background_tasks: BackgroundTasks, settings: Settings = Depends(get_settings)):
    job_id = str(uuid.uuid4())
    
    # Run async pipeline
    background_tasks.add_task(run_memo_pipeline, job_id, request, settings)
    
    return MemoGenerateResponse(
        job_id=job_id,
        status="processing",
        generated_at=str(uuid.uuid1())
    )

@app.get("/api/v2/memo/status/{job_id}", response_model=MemoGenerateResponse)
async def get_memo_status(job_id: str):
    if job_id not in JOB_STATUS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    status = JOB_STATUS[job_id]
    sections = JOB_RESULTS.get(job_id, [])
    
    urls = JOB_RESULTS.get(job_id + "_urls", {})
    
    return MemoGenerateResponse(
        job_id=job_id,
        status=status,
        sections=sections if isinstance(sections, list) else None,
        download_urls=urls,
        audit_trail_url=urls.get("audit_trail") if urls else None,
        generated_at=""
    )

@app.get("/api/v2/memo/download/{job_id}")
async def download_memo(job_id: str, fmt: str, settings: Settings = Depends(get_settings)):
    if fmt == "docx":
        path = f"{settings.output_dir}/{job_id}.docx"
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "pptx":
        path = f"{settings.output_dir}/{job_id}.pptx"
        media = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif fmt == "json":
        path = f"{settings.output_dir}/{job_id}_audit.json"
        media = "application/json"
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
        
    if os.path.exists(path):
        return FileResponse(path, media_type=media, filename=f"{job_id}.{fmt}")
    
    raise HTTPException(status_code=404, detail="File not found")

# ======================= PHASE 3 ROUTES =======================

from app.schemas_v3 import ComplianceGenerateRequest, ComplianceGenerateResponse, ReviewUpdate
from app.pipeline_v3 import start_compliance_job, get_job_status, update_job_response, regenerate_exports, get_chroma_client as get_chroma_client_v3, questionnaires_db
from app.agents.kb_retriever import KBRetrieverAgent
from app.agents.intake_parser import IntakeParserAgent
import json
import shutil

@app.post("/api/v3/compliance/upload-kb")
async def upload_kb(files: list[UploadFile] = File(...), settings: Settings = Depends(get_settings)):
    client = get_chroma_client_v3(settings)
    retriever = KBRetrieverAgent(client)
    
    temp_dir = f"/tmp/kb_upload_{uuid.uuid4().hex[:8]}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        for file in files:
            filepath = os.path.join(temp_dir, file.filename)
            with open(filepath, "wb") as f:
                f.write(await file.read())
            # For simplicity, pass doc_type="other" and empty description, or extract from name if possible
            retriever.process_file(filepath, doc_type="other", description="Uploaded KB doc")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    return {"status": "success", "message": f"Indexed {len(files)} files into KB"}

@app.post("/api/v3/compliance/upload-questionnaire")
async def upload_questionnaire(file: UploadFile = File(...)):
    if file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="XLSX files are strictly forbidden (DMZ rule).")
        
    parser = IntakeParserAgent()
    content = await file.read()
    
    try:
        questions = parser.parse_questionnaire(file.filename, content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    session_id = uuid.uuid4().hex[:8]
    questionnaires_db[session_id] = questions
    
    framework = questions[0].framework if questions else "unknown"
    domains = list(set([q.domain for q in questions if q.domain]))
    
    return {
        "questionnaire_session_id": session_id,
        "framework": framework,
        "total_questions": len(questions),
        "domains": domains
    }

@app.post("/api/v3/compliance/generate", response_model=ComplianceGenerateResponse)
async def generate_compliance(request: ComplianceGenerateRequest, background_tasks: BackgroundTasks, settings: Settings = Depends(get_settings)):
    if request.questionnaire_session_id not in questionnaires_db:
        raise HTTPException(status_code=404, detail="Questionnaire session not found")
        
    job_id = start_compliance_job(request, background_tasks, settings)
    return get_job_status(job_id)

@app.get("/api/v3/compliance/status/{job_id}", response_model=ComplianceGenerateResponse)
async def get_compliance_status(job_id: str):
    try:
        return get_job_status(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

@app.patch("/api/v3/compliance/review/{job_id}/{question_id}")
async def review_compliance_response(job_id: str, question_id: str, update: ReviewUpdate, settings: Settings = Depends(get_settings)):
    try:
        success = update_job_response(job_id, question_id, update.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Question not found in job")
        
        # Regenerate exports after review update
        regenerate_exports(job_id, settings)
        return {"status": "success"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

@app.get("/api/v3/compliance/download/{job_id}")
async def download_compliance(job_id: str, fmt: str, settings: Settings = Depends(get_settings)):
    if fmt == "csv":
        path = f"{settings.output_dir}/{job_id}_questionnaire.csv"
        media = "text/csv"
    elif fmt == "docx":
        path = f"{settings.output_dir}/{job_id}_questionnaire.docx"
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "json":
        path = f"{settings.output_dir}/{job_id}_questionnaire.json"
        media = "application/json"
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
        
    if os.path.exists(path):
        return FileResponse(path, media_type=media, filename=f"{job_id}_questionnaire.{fmt}")
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
