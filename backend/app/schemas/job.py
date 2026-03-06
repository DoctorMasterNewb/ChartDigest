from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobCreate(BaseModel):
    provider_mode: str = "ollama"


class JobRead(BaseModel):
    id: int
    case_id: int
    provider_mode: str
    provider_name: str
    status: str
    progress: int
    current_step: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    running_summary: str | None = None
    final_summary: str | None = None

    model_config = {"from_attributes": True}

