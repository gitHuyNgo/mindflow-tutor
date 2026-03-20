from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    # Database
    mongo_url: str
    db_name: str
    cors_origins: str = "*"
    
    # API Keys
    openai_api_key: str
    elevenlabs_api_key: str
    tavily_api_key: str
    llama_cloud_api_key: str
    
    # Agora
    agora_app_id: str
    
    # Paths
    data_dir: str = "/app/data"
    chroma_dir: str = "/app/data/chroma_db"
    uploads_dir: str = "/app/data/uploads"
    
    # ElevenLabs settings
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    elevenlabs_model: str = "eleven_turbo_v2_5"
    
    # OpenAI settings
    openai_model: str = "gpt-4o"
    
    # Audio settings
    sample_rate: int = 16000
    vad_threshold: float = 0.3
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()