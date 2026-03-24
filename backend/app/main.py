import os
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import GenerateRequest, GenerateResponse
from app.config import Settings
from app.pipeline import run_pipeline
from app.templates import PRESETS

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
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/v1/templates")
async def get_templates():
    return PRESETS

@app.get("/health")
async def health_check():
    return {"status": "ok"}
