from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AppSettings(TimestampMixin, Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_mode: Mapped[str] = mapped_column(String(32), default="ollama")
    ollama_base_url: Mapped[str] = mapped_column(String(255), default="http://127.0.0.1:11434")
    ollama_model: Mapped[str] = mapped_column(String(128), default="llama3.1:8b")

