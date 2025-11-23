import pytest
from src.collectors.camara import CamaraCollector
from src.collectors.senado import SenadoCollector
from src.collectors.alesp import AlespCollector
from src.collectors.municipal import MunicipalCollector
from src.core.config import settings

@pytest.mark.asyncio
async def test_camara_collector_real():
    """Test Camara collector against real API."""
    collector = CamaraCollector()
    # Fetch just 1 item from last 5 days
    items = collector.collect(days_back=5, limit=1)
    
    # API might be down or empty, but it shouldn't crash
    assert isinstance(items, list)
    if items:
        item = items[0]
        assert item.source == "camara_deputados"
        assert item.level == "federal"

@pytest.mark.asyncio
async def test_senado_collector_real():
    """Test Senado collector (Google Search)."""
    if not settings.GOOGLE_SEARCH_API_KEY:
        pytest.skip("Google API Key not set")
        
    collector = SenadoCollector()
    items = collector.collect(days_back=5, limit=1)
    
    assert isinstance(items, list)
    if items:
        item = items[0]
        assert item.source == "senado_federal"

@pytest.mark.asyncio
async def test_alesp_collector_real():
    """Test ALESP collector (Google Search)."""
    if not settings.GOOGLE_SEARCH_API_KEY:
        pytest.skip("Google API Key not set")

    collector = AlespCollector()
    items = collector.collect(days_back=5, limit=1)
    
    assert isinstance(items, list)

@pytest.mark.asyncio
async def test_municipal_collector_real():
    """Test Municipal collector (Google Search)."""
    if not settings.GOOGLE_SEARCH_API_KEY:
        pytest.skip("Google API Key not set")

    collector = MunicipalCollector()
    items = collector.collect(days_back=5, limit=1)
    
    assert isinstance(items, list)
