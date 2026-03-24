import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from app.schemas import GenerateRequest, GenerateResponse
from app.config import Settings
from app.agents import profiler, generator, validator, formatter

async def run_pipeline(request: GenerateRequest, settings: Settings) -> GenerateResponse:
    job_id = str(uuid.uuid4())

    if request.scenario.use_llm_profiler:
        if not request.scenario.natural_language:
            raise HTTPException(422, "natural_language must be provided when use_llm_profiler is true")
        profile = await profiler.generate_profile(request.scenario.natural_language, settings)
        
        if request.profile_override:
            override_data = request.profile_override.model_dump(exclude_unset=True)
            profile_data = profile.model_dump()
            profile_data.update(override_data)
            profile = type(profile)(**profile_data)
    elif request.profile_override:
        profile = request.profile_override
    else:
        raise HTTPException(422, "Either use_llm_profiler or profile_override must be provided")

    data, corr_matrix = generator.generate(profile, seed=request.seed)

    data, report = validator.validate(data, profile, corr_matrix, request.privacy, seed=request.seed)

    formatter.export(data, request.output_format, job_id, settings.output_dir)

    return GenerateResponse(
        job_id=job_id,
        status="completed",
        download_url=f"/api/v1/download/{job_id}",
        profile_used=profile,
        validation_report=report,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
