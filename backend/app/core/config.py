from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR.parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHART_DIGEST_", env_file=".env", extra="ignore")

    app_name: str = "Chart Digest"
    database_url: str = f"sqlite:///{(DATA_DIR / 'chart_digest.db').as_posix()}"
    uploads_dir: str = (DATA_DIR / "uploads").as_posix()
    extracted_dir: str = (DATA_DIR / "extracted").as_posix()
    provider_mode: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    chunk_target_chars: int = 2200
    chunk_overlap_chars: int = 250


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.extracted_dir).mkdir(parents=True, exist_ok=True)
    return settings

