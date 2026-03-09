from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.case import Case
from app.schemas.episode_state import EpisodeStateV2, EpisodeStateVersionCreate
from app.services import episode_state_service


def _valid_state() -> dict:
    source_ref = {
        "source_doc_id": "doc-1",
        "page_start": 1,
        "page_end": 1,
        "char_start": 0,
        "char_end": 20,
        "chunk_id": "chunk-1",
        "note_id": "note-1",
        "quoted_text_preview": "Work status modified duty",
    }
    return {
        "case_metadata": {"case_id": "case-1"},
        "injury_profile": {"body_part": "lumbar spine"},
        "events": [
            {
                "event_id": "evt-1",
                "date": "2024-01-01",
                "date_precision": "exact",
                "event_type": "visit",
                "title": "Initial evaluation",
                "summary": "Patient evaluated for low back pain.",
                "participants": ["Dr. Smith"],
                "related_entities": ["dx-1"],
                "source_refs": [source_ref],
                "confidence": 0.95,
                "conflict_flag": False,
            }
        ],
        "diagnoses": [],
        "medications": [],
        "procedures": [],
        "imaging_and_tests": [],
        "therapy_blocks": [
            {
                "therapy_block_id": "tb-1",
                "discipline": "pt",
                "start_date": "2024-01-03",
                "end_date": None,
                "ordered_visits": 12,
                "completed_visits": 2,
                "key_objective_findings": ["Limited ROM"],
                "key_subjective_findings": ["Pain 6/10"],
                "trend_assessment": "improving",
                "plateau_flag": False,
                "related_events": ["evt-1"],
                "source_refs": [source_ref],
            }
        ],
        "work_status_history": [
            {
                "status_id": "ws-1",
                "date": "2024-01-01",
                "duty_status": "modified_duty",
                "restrictions": ["No repetitive bending"],
                "lifting_limit": "10 lbs",
                "positional_limits": ["stand 20 min/hour"],
                "rationale": "acute pain flare",
                "source_refs": [source_ref],
                "supersedes_status_id": None,
            }
        ],
        "current_status": {"clinical_state": "ongoing treatment"},
        "conflicts": [],
        "missing_information": [],
        "provenance_index": {"evt-1": [source_ref]},
        "state_metrics": {"coverage": 0.8},
    }


def test_episode_state_validation_rejects_invalid_enum():
    payload = _valid_state()
    payload["work_status_history"][0]["duty_status"] = "part_time"

    with pytest.raises(ValidationError):
        EpisodeStateV2.model_validate(payload)


def test_create_episode_state_versions(test_db):
    case = Case(title="Case for episode state", description=None)
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    first = episode_state_service.create_episode_state_version(
        test_db,
        case.id,
        EpisodeStateVersionCreate(canonical_state=EpisodeStateV2.model_validate(_valid_state())),
    )
    second = episode_state_service.create_episode_state_version(
        test_db,
        case.id,
        EpisodeStateVersionCreate(canonical_state=EpisodeStateV2.model_validate(_valid_state()), diff={"events": "+0"}),
    )

    assert first.version_number == 1
    assert second.version_number == 2

    latest = episode_state_service.get_latest_episode_state_version(test_db, case.id)
    assert latest is not None
    assert latest.version_number == 2
