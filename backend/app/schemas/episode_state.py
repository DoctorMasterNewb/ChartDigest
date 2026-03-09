from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatePrecision(str, Enum):
    exact = "exact"
    month = "month"
    year = "year"
    unknown = "unknown"


class DutyStatus(str, Enum):
    full_duty = "full_duty"
    modified_duty = "modified_duty"
    off_work = "off_work"
    unknown = "unknown"


class SourceRef(StrictModel):
    source_doc_id: str
    page_start: int
    page_end: int
    char_start: int
    char_end: int
    chunk_id: str | None = None
    note_id: str | None = None
    quoted_text_preview: str


class EventV2(StrictModel):
    event_id: str
    date: date | None = None
    date_precision: DatePrecision = DatePrecision.unknown
    event_type: str
    title: str
    summary: str
    participants: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    conflict_flag: bool = False


class TherapyBlockV2(StrictModel):
    therapy_block_id: str
    discipline: str
    start_date: date | None = None
    end_date: date | None = None
    ordered_visits: int | None = None
    completed_visits: int | None = None
    key_objective_findings: list[str] = Field(default_factory=list)
    key_subjective_findings: list[str] = Field(default_factory=list)
    trend_assessment: str | None = None
    plateau_flag: bool = False
    related_events: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(min_length=1)


class WorkStatusItemV2(StrictModel):
    status_id: str
    date: date | None = None
    duty_status: DutyStatus
    restrictions: list[str] = Field(default_factory=list)
    lifting_limit: str | None = None
    positional_limits: list[str] = Field(default_factory=list)
    rationale: str | None = None
    source_refs: list[SourceRef] = Field(min_length=1)
    supersedes_status_id: str | None = None


class EpisodeStateV2(StrictModel):
    case_metadata: dict[str, Any]
    injury_profile: dict[str, Any]
    events: list[EventV2] = Field(default_factory=list)
    diagnoses: list[dict[str, Any]] = Field(default_factory=list)
    medications: list[dict[str, Any]] = Field(default_factory=list)
    procedures: list[dict[str, Any]] = Field(default_factory=list)
    imaging_and_tests: list[dict[str, Any]] = Field(default_factory=list)
    therapy_blocks: list[TherapyBlockV2] = Field(default_factory=list)
    work_status_history: list[WorkStatusItemV2] = Field(default_factory=list)
    current_status: dict[str, Any]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    missing_information: list[dict[str, Any]] = Field(default_factory=list)
    provenance_index: dict[str, list[SourceRef]] = Field(default_factory=dict)
    state_metrics: dict[str, Any]


class EpisodeStateVersionCreate(StrictModel):
    canonical_state: EpisodeStateV2
    diff: dict[str, Any] | None = None
    stability_score: float | None = None


class EpisodeStateVersionRead(StrictModel):
    id: int
    case_id: int
    version_number: int
    canonical_state: EpisodeStateV2
    diff: dict[str, Any] | None = None
    stability_score: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
