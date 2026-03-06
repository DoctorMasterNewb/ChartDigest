from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SettingsRead(BaseModel):
    provider_mode: str
    ollama_base_url: str
    ollama_model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    provider_mode: str | None = Field(default=None)
    ollama_base_url: str | None = Field(default=None)
    ollama_model: str | None = Field(default=None)

