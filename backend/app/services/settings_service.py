from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.app_settings import AppSettings
from app.providers.base import ProviderConfig
from app.schemas.settings import SettingsUpdate


def get_or_create_settings(db: Session) -> AppSettings:
    settings_row = db.scalar(select(AppSettings).where(AppSettings.id == 1))
    if settings_row is not None:
        return settings_row

    defaults = get_settings()
    settings_row = AppSettings(
        id=1,
        provider_mode=defaults.provider_mode,
        ollama_base_url=defaults.ollama_base_url,
        ollama_model=defaults.ollama_model,
    )
    db.add(settings_row)
    db.commit()
    db.refresh(settings_row)
    return settings_row


def update_settings(db: Session, payload: SettingsUpdate) -> AppSettings:
    settings_row = get_or_create_settings(db)
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(settings_row, field, value)
    db.add(settings_row)
    db.commit()
    db.refresh(settings_row)
    return settings_row


def resolve_provider_settings(db: Session, override: SettingsUpdate | None = None) -> ProviderConfig:
    settings_row = get_or_create_settings(db)
    updates = override.model_dump(exclude_none=True) if override else {}
    return ProviderConfig(
        provider_mode=updates.get("provider_mode", settings_row.provider_mode),
        ollama_base_url=updates.get("ollama_base_url", settings_row.ollama_base_url),
        ollama_model=updates.get("ollama_model", settings_row.ollama_model),
    )

