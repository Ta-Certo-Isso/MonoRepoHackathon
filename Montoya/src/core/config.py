import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    """
    Application settings managed by Pydantic.
    Reads from environment variables and .env file.
    """
    # API Keys
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_VIDEOS_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_VIDEOS_API_KEY: Optional[str] = None
    AZURE_OPENAI_VIDEOS_MODEL: str = "sora-2"
    AZURE_OPENAI_VIDEOS_SIZE: str = "720x1280"
    
    # Collection Settings
    DEFAULT_DAYS_BACK: int = 30
    DEFAULT_LIMIT_PER_SOURCE: int = 10
    INCLUDE_MUNICIPAL: bool = True
    MAX_WORKERS: int = 10
    
    # Server Settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

# Global settings instance
settings = Settings()
