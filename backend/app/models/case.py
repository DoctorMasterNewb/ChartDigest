from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="case", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="case", cascade="all, delete-orphan")

