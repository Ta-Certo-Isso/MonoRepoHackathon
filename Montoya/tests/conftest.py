import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.core.config import settings

# Force testing environment
settings.ENVIRONMENT = "testing"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def client():
    """Async client for testing the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
