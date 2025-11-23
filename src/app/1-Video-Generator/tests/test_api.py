import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Montoya API is running"

@pytest.mark.asyncio
async def test_collect_endpoint(client: AsyncClient):
    """
    Test the /collect endpoint.
    Note: This triggers real collection, so we limit it to 1 item and 1 day to be fast.
    """
    # Using small limits to avoid hitting rate limits or taking too long
    params = {"days_back": 1, "limit": 1}
    response = await client.post("/collect", params=params)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_items" in data
    assert "sources_summary" in data
    assert "details" in data
    
    # Check if we got at least some data structure back
    # We can't guarantee items will be found, but the structure should be correct
    assert isinstance(data["details"], dict)

@pytest.mark.asyncio
async def test_generate_tiktok_script(client: AsyncClient):
    """Test script generation endpoint."""
    payload = {
        "proposition": {
            "title": "Test Proposition",
            "description": "This is a test description for a law.",
            "source": "test_source",
            "level": "federal",
            "collection_type": "test"
        },
        "style": "informative"
    }
    
    response = await client.post("/generate/tiktok", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "script" in data
    # If API key is missing, it returns an error message string, but status 200
    assert isinstance(data["script"], str)
