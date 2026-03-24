import json
import httpx
from jinja2 import Environment, FileSystemLoader
from google import genai
from pydantic import ValidationError
from fastapi import HTTPException
from app.schemas import StatisticalProfile
from app.config import Settings
import os

def render_prompt(scenario: str) -> str:
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'prompts')))
    template = env.get_template('profile_suggest.j2')
    return template.render(user_scenario=scenario)

async def generate_profile(scenario: str, settings: Settings) -> StatisticalProfile:
    rendered_prompt = render_prompt(scenario)
    
    if settings.llm_provider == "google":
        client = genai.Client(api_key=settings.llm_api_key)
        
        response = client.models.generate_content(
            model=settings.llm_model,
            contents=rendered_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": StatisticalProfile,
                "temperature": 0.2
            },
        )
        raw_json = response.text
    elif settings.llm_provider == "openai":
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": rendered_prompt}],
                    "response_format": {
                        "type": "json_schema", 
                        "json_schema": {"name": "StatisticalProfile", "schema": StatisticalProfile.model_json_schema(), "strict": True}
                    },
                    "temperature": 0.2,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            raw_json = resp.json()["choices"][0]["message"]["content"]
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
        
    try:
        data = json.loads(raw_json)
        return StatisticalProfile(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(422, f"LLM produced invalid profile: {e}")
