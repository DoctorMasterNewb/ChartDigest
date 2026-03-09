from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.episode_state_version import EpisodeStateVersion
from app.schemas.episode_state import EpisodeStateV2, EpisodeStateVersionCreate


class EpisodeStateValidationError(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__("Episode state validation failed")
        self.errors = errors


def create_episode_state_version(db: Session, case_id: int, payload: EpisodeStateVersionCreate) -> EpisodeStateVersion:
    case = db.get(Case, case_id)
    if case is None:
        raise ValueError("Case not found")

    try:
        validated_state = EpisodeStateV2.model_validate(payload.canonical_state)
    except ValidationError as exc:
        raise EpisodeStateValidationError(exc.errors()) from exc

    current_max = db.scalar(
        select(func.max(EpisodeStateVersion.version_number)).where(EpisodeStateVersion.case_id == case_id)
    )
    next_version = (current_max or 0) + 1

    state_version = EpisodeStateVersion(
        case_id=case_id,
        version_number=next_version,
        canonical_state_json=validated_state.model_dump(mode="json"),
        diff_json=payload.diff,
        stability_score=payload.stability_score,
    )
    db.add(state_version)
    db.commit()
    db.refresh(state_version)
    return state_version


def get_latest_episode_state_version(db: Session, case_id: int) -> EpisodeStateVersion | None:
    return db.scalar(
        select(EpisodeStateVersion)
        .where(EpisodeStateVersion.case_id == case_id)
        .order_by(EpisodeStateVersion.version_number.desc())
    )


def list_episode_state_versions(db: Session, case_id: int) -> list[EpisodeStateVersion]:
    return list(
        db.scalars(
            select(EpisodeStateVersion)
            .where(EpisodeStateVersion.case_id == case_id)
            .order_by(EpisodeStateVersion.version_number.desc())
        )
    )


def get_episode_state_version(db: Session, case_id: int, version_number: int) -> EpisodeStateVersion | None:
    return db.scalar(
        select(EpisodeStateVersion).where(
            EpisodeStateVersion.case_id == case_id,
            EpisodeStateVersion.version_number == version_number,
        )
    )
