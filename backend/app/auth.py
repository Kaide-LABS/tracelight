from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import Settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: str = Security(api_key_header),
    settings: Settings = None,
) -> str:
    """
    Verify the API key from the X-API-Key header.
    In demo mode, authentication is bypassed.
    """
    if settings and settings.demo_mode:
        return "demo"
    if not settings or not settings.auth_enabled:
        return "unauthenticated"
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
