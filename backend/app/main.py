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

@app.get("/health")
async def health_check():
    return {"status": "ok"}
