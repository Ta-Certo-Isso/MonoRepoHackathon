import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.collectors.camara import CamaraCollector
from src.services.tiktok_service import tiktok_service
from src.services.sora_service import sora_video_service
from src.core.config import settings, BASE_DIR
from src.core.database import Base
from src.models.db_models import DBProposition

# Setup Test DB
TEST_DATABASE_URL = "sqlite:///./test_montoya.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure we are in testing mode
settings.ENVIRONMENT = "production_test"
@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    engine.dispose()
    if os.path.exists("./test_montoya.db"):
        os.remove("./test_montoya.db")

@pytest.mark.asyncio
async def test_full_production_flow_with_sora(db_session):
    """
    Test the complete flow with Sora:
    1. Collect -> DB.
    2. Script -> DB.
    3. Sora Video -> arquivo local.
    """
    print("\n[1] Starting Collection (Camara)...")
    collector = CamaraCollector()
    items = collector.collect(days_back=3, limit=1)
    
    if not items:
        pytest.skip("No items found in Camara to test with.")
        
    proposition = items[0]
    print(f"    Found: {proposition.title}")
    
    db_prop = DBProposition(
        title=proposition.title,
        description=proposition.description,
        content=proposition.content,
        link=proposition.link,
        date=proposition.date,
        source=proposition.source,
        level=proposition.level,
        collection_type=proposition.collection_type
    )
    db_session.add(db_prop)
    db_session.commit()
    
    print("\n[2] Generating TikTok Script...")
    script = tiktok_service.generate_script(proposition, style="viral", db=db_session)
    assert script, "Script generation failed"
    print("    Script generated successfully.")
    
    if sora_video_service is None or not settings.AZURE_OPENAI_VIDEOS_API_KEY:
        pytest.skip("Sora não configurado para testes.")

    print("\n[3] Generating Video (Sora)...")
    output_dir = BASE_DIR / "output" / "videos" / "tests"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = sora_video_service.generate_video_from_script(
        [{"audio": script, "visual": ""}],
        base_filename="test_flow",
        output_dir=output_dir,
        max_segments=1,
        segment_duration=12,
    )

    assert os.path.exists(result_path), "Arquivo de vídeo não foi salvo."
    print(f"    Sora Result: {result_path}")
