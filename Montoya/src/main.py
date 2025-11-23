import math
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.core.config import settings, BASE_DIR
from src.core.logging import setup_logging, get_logger
from src.core.database import init_db, get_db
from src.models.schemas import CollectionSummary, TikTokScriptRequest, VideoGenerationRequest
from src.services.collector_service import collector_service
from src.services.tiktok_service import tiktok_service
from src.services.sora_service import sora_video_service

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize DB
init_db()

app = FastAPI(
    title="Montoya API",
    description="API for collecting legislative data and generating content.",
    version="2.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Montoya API is running", "environment": settings.ENVIRONMENT}

@app.post("/collect", response_model=CollectionSummary)
async def trigger_collection(days_back: int = 30, limit: int = 10, db: Session = Depends(get_db)):
    """
    Trigger a full data collection from all sources.
    """
    try:
        summary = await collector_service.run_collection(days_back, limit, db)
        return summary
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/tiktok")
async def generate_tiktok_script(request: TikTokScriptRequest, db: Session = Depends(get_db)):
    """
    Generate a TikTok script for a specific proposition.
    """
    script = tiktok_service.generate_script(request.proposition, request.style, db)
    return {"script": script}

def _split_text(text: str, parts: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunk_size = math.ceil(len(words) / parts)
    chunks = [" ".join(words[i : i + chunk_size]).strip() for i in range(0, len(words), chunk_size)]
    while len(chunks) < parts:
        chunks.append("")
    return chunks[:parts]


def _prepare_segments(script: str, desired: int = 2) -> list[dict[str, str]]:
    cleaned = script.strip()
    if not cleaned:
        raise ValueError("Script vazio; nada para gerar.")

    has_tags = "[AUDIO" in cleaned and "[VISUAL" in cleaned
    if has_tags:
        audio_sections = re.findall(r"\[AUDIO\]\s*(.*?)\s*(?=\[[A-Z]+|\Z)", cleaned, flags=re.DOTALL | re.IGNORECASE)
        visual_sections = re.findall(r"\[VISUAL\]\s*(.*?)\s*(?=\[[A-Z]+|\Z)", cleaned, flags=re.DOTALL | re.IGNORECASE)
        sections = []
        for idx, audio in enumerate(audio_sections):
            visual = visual_sections[idx] if idx < len(visual_sections) else ""
            if audio.strip():
                sections.append({"audio": audio.strip(), "visual": visual.strip()})
        if sections:
            return sections[:desired]

    audio_chunks = _split_text(cleaned, desired)
    return [{"audio": chunk or cleaned, "visual": ""} for chunk in audio_chunks]


@app.post("/generate/video")
async def generate_video(request: VideoGenerationRequest):
    """
    Generate a video using the Azure OpenAI (Sora) integration.
    """
    if sora_video_service is None:
        raise HTTPException(status_code=500, detail="Serviço do Sora indisponível.")

    try:
        segments = _prepare_segments(request.script, desired=2)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    base_dir = BASE_DIR / "output" / "videos" / "api"
    base_dir.mkdir(parents=True, exist_ok=True)

    result_path = sora_video_service.generate_video_from_script(
        segments,
        base_filename=re.sub(r"\W+", "_", request.proposition.title or "video").lower()[:50],
        output_dir=base_dir,
        max_segments=2,
        segment_duration=min(request.max_duration_seconds or 12, 12),
    )

    return {"result": str(result_path)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
