from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
from app.logging_config import get_logger

log = get_logger("middleware")

def get_real_address(request: Request) -> str:
    if request.client is None:
        return "127.0.0.1"
    return request.client.host

limiter = Limiter(key_func=get_real_address)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        client_host = request.client.host if request.client else "unknown"
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration, 1),
            client=client_host,
        )
        return response