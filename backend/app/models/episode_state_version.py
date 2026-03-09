from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class EpisodeStateVersion(TimestampMixin, Base):
    __tablename__ = "episode_state_versions"
    __table_args__ = (UniqueConstraint("case_id", "version_number", name="uq_episode_state_case_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    canonical_state_json: Mapped[dict] = mapped_column(JSON)
    diff_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stability_score: Mapped[float | None] = mapped_column(nullable=True)
