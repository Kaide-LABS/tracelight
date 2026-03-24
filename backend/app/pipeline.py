import uuid
import time
from datetime import datetime, timezone
from fastapi import HTTPException
from app.schemas import GenerateRequest, GenerateResponse
from app.config import Settings
from app.agents import profiler, generator, validator, formatter
from app.database import create_job, update_job
from app.logging_config import get_logger

log = get_logger("pipeline_v1")

async def run_pipeline(request: GenerateRequest, settings: Settings) -> GenerateResponse:
    job_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    
    await create_job(job_id, "v1", request.model_dump())
    
    log.info("pipeline_started", job_id=job_id, phase="v1", use_llm=request.scenario.use_llm_profiler)

    try:
        if request.scenario.use_llm_profiler:
            if not request.scenario.natural_language:
                raise HTTPException(422, "natural_language must be provided when use_llm_profiler is true")
            
            p_start = time.perf_counter()
            profile = await profiler.generate_profile(request.scenario.natural_language, settings)
            log.info("profiler_completed", job_id=job_id, duration_ms=(time.perf_counter() - p_start) * 1000)
            
            if request.profile_override:
                override_data = request.profile_override.model_dump(exclude_unset=True)
                profile_data = profile.model_dump()
                profile_data.update(override_data)
                profile = type(profile)(**profile_data)
        elif request.profile_override:
            profile = request.profile_override
        else:
            raise HTTPException(422, "Either use_llm_profiler or profile_override must be provided")

        g_start = time.perf_counter()
        data, corr_matrix = generator.generate(profile, seed=request.seed)
        log.info("generator_completed", job_id=job_id, rows=len(data), duration_ms=(time.perf_counter() - g_start) * 1000)

        data, report = validator.validate(data, profile, corr_matrix, request.privacy, seed=request.seed)

        formatter.export(data, request.output_format, job_id, settings.output_dir)
        
        response = GenerateResponse(
            job_id=job_id,
            status="completed",
            download_url=f"/api/v1/download/{job_id}",
            profile_used=profile,
            validation_report=report,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        await update_job(job_id, "completed", response.model_dump())
        log.info("pipeline_completed", job_id=job_id, status="completed", total_duration_ms=(time.perf_counter() - start_time) * 1000)
        
        return response
    except HTTPException as e:
        await update_job(job_id, "failed", error=str(e.detail))
        log.error("pipeline_failed", job_id=job_id, error=str(e.detail))
        raise
    except Exception as e:
        await update_job(job_id, "failed", error=str(e))
        log.error("pipeline_failed", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(500, "Internal server error")
