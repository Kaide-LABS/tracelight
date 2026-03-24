import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings

@pytest.fixture
def settings():
    return Settings(demo_mode=True, api_key="test-key-123", auth_enabled=True, rate_limit_enabled=False)

@pytest.fixture
def client(settings):
    """Test client with demo mode enabled (no LLM calls)."""
    # Override settings dependency
    from app.config import get_settings
    app.dependency_overrides[get_settings] = lambda: settings
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()
