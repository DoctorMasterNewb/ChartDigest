from __future__ import annotations

from pydantic import BaseModel

from app.schemas.settings import SettingsUpdate


class ProviderTestRequest(BaseModel):
    override_settings: SettingsUpdate | None = None


class ProviderTestResponse(BaseModel):
    ok: bool
    provider_name: str
    message: str

