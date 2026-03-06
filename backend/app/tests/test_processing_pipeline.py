from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.models.case import Case
from app.models.document import Document
from app.models.job import Job
from app.providers.base import ProviderConfig
from app.services import processing_service


class FakeProvider:
    name = "fake"

    async def test_connection(self):
        return True, "ok"

    async def summarize_chunk(self, prompt: str) -> str:
        if "Turn this running chronology summary" in prompt:
            return "FINAL SUMMARY"
        return "RUNNING UPDATE"


@pytest.mark.asyncio
async def test_processing_pipeline_happy_path(test_db, monkeypatch, tmp_path):
    case = Case(title="Pipeline test", description=None)
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    text_path = tmp_path / "doc.txt"
    text_path.write_text("Jan 1, 2024 Intake.\n\nJan 2, 2024 Follow-up.", encoding="utf-8")

    document = Document(
        case_id=case.id,
        filename="doc.txt",
        content_type="text/plain",
        extension=".txt",
        status="ingested",
        file_path=str(text_path),
        text_path=str(text_path),
        text_length=42,
        metadata_json="{}",
    )
    test_db.add(document)
    test_db.commit()

    monkeypatch.setattr(processing_service, "build_provider", lambda config: FakeProvider())

    job = await processing_service.start_case_processing(test_db, case.id, payload=type("Payload", (), {"provider_mode": "ollama"})())
    task = processing_service._running_tasks[job.id]
    await task

    refreshed = processing_service.get_job_status(test_db, job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.running_summary is not None
    assert refreshed.final_summary == "FINAL SUMMARY"
