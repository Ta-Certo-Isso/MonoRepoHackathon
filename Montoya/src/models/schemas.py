from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Proposition(BaseModel):
    """
    Standardized model for a legislative proposition or news item.
    """
    title: str = Field(..., description="Title or main header of the item")
    description: Optional[str] = Field(None, description="Short description or summary")
    content: Optional[str] = Field(None, description="Full content or body text")
    link: Optional[str] = Field(None, description="URL to the source")
    date: Optional[str] = Field(None, description="Date of publication or presentation (YYYY-MM-DD)")
    source: str = Field(..., description="Source name (e.g., 'camara_deputados', 'senado_federal')")
    level: str = Field(..., description="Legislative level ('federal', 'estadual', 'municipal')")
    collection_type: str = Field(..., description="Method of collection ('api', 'google_search', 'scraping')")
    relevance_score: Optional[int] = Field(None, description="Calculated relevance score")

class CollectionResult(BaseModel):
    """
    Result of a collection run for a specific source.
    """
    source: str
    items: List[Proposition]
    count: int
    timestamp: datetime = Field(default_factory=datetime.now)

class CollectionSummary(BaseModel):
    """
    Summary of all collections.
    """
    total_items: int
    sources_summary: dict[str, int]
    timestamp: datetime = Field(default_factory=datetime.now)
    details: dict[str, List[Proposition]]

class TikTokScriptRequest(BaseModel):
    """
    Request model for generating a TikTok script.
    """
    proposition: Proposition
    style: Optional[str] = "informative"

class VideoGenerationRequest(BaseModel):
    """
    Request model for generating a video.
    """
    script: str
    proposition: Proposition
    max_duration_seconds: Optional[int] = Field(
        default=None,
        ge=4,
        le=60,
        description="Duração desejada (em segundos). Padrão: 30s, respeitando o limite de ~8s por segmento do modelo."
    )
