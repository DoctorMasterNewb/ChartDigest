from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import session as session_module
from app.models.case import Case
from app.models.document import Document
from app.models.job import Job
from app.models.summary import Summary
from app.providers.factory import build_provider
from app.schemas.job import JobCreate, JobRead
from app.schemas.provider import ProviderTestResponse
from app.services.chunking import split_into_chunks
from app.services.document_service import load_document_text
from app.services.settings_service import resolve_provider_settings

_running_tasks: dict[int, asyncio.Task[None]] = {}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def test_provider_connection(config) -> ProviderTestResponse:
    provider = build_provider(config)
    ok, message = await provider.test_connection()
    return ProviderTestResponse(ok=ok, provider_name=provider.name, message=message)


async def start_case_processing(db: Session, case_id: int, payload: JobCreate) -> JobRead:
    case = db.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise ValueError("Case not found")

    documents = list(db.scalars(select(Document).where(Document.case_id == case_id).order_by(Document.created_at.asc())))
    if not documents:
        raise ValueError("Upload at least one document before processing")

    config = resolve_provider_settings(db)
    if payload.provider_mode != config.provider_mode:
        config.provider_mode = payload.provider_mode

    job = Job(
        case_id=case_id,
        provider_mode=config.provider_mode,
        provider_name=config.provider_mode,
        status="queued",
        progress=0,
        current_step="Queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _running_tasks[job.id] = asyncio.create_task(_run_job(job.id, config))
    return _serialize_job(db, job.id)


def get_job_status(db: Session, job_id: int) -> JobRead | None:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        return None
    return _serialize_job(db, job_id)


async def _run_job(job_id: int, config) -> None:
    db = session_module.SessionLocal()
    try:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if job is None:
            return

        provider = build_provider(config)
        documents = list(db.scalars(select(Document).where(Document.case_id == job.case_id).order_by(Document.created_at.asc())))
        all_text = "\n\n".join(load_document_text(document) for document in documents)
        chunks = split_into_chunks(all_text)
        if not chunks:
            raise ValueError("No text chunks were generated")

        job.status = "running"
        job.started_at = _utcnow()
        job.current_step = "Testing provider"
        db.add(job)
        db.commit()

        ok, message = await provider.test_connection()
        if not ok:
            raise RuntimeError(message)

        db.execute(delete(Summary).where(Summary.job_id == job.id))
        db.commit()

        running_summary = ""
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            job.current_step = f"Summarizing chunk {index}/{total_chunks}"
            job.progress = int(((index - 1) / max(total_chunks, 1)) * 100)
            db.add(job)
            db.commit()

            prompt = _build_chunk_prompt(chunk.content, chunk.anchor_hint, running_summary)
            chunk_summary = await provider.summarize_chunk(prompt)
            running_summary = _merge_running_summary(running_summary, chunk_summary)

            summary = Summary(
                case_id=job.case_id,
                job_id=job.id,
                summary_type="running",
                chunk_index=index - 1,
                total_chunks=total_chunks,
                content=running_summary,
            )
            db.add(summary)
            db.commit()

        job.current_step = "Building final summary"
        job.progress = 95
        db.add(job)
        db.commit()

        final_prompt = _build_final_prompt(running_summary)
        final_summary = await provider.summarize_chunk(final_prompt)
        db.add(
            Summary(
                case_id=job.case_id,
                job_id=job.id,
                summary_type="final",
                chunk_index=None,
                total_chunks=total_chunks,
                content=final_summary,
            )
        )
        job.status = "completed"
        job.progress = 100
        job.current_step = "Completed"
        job.finished_at = _utcnow()
        db.add(job)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.scalar(select(Job).where(Job.id == job_id))
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.current_step = "Failed"
            job.finished_at = _utcnow()
            db.add(job)
            db.commit()
    finally:
        db.close()
        _running_tasks.pop(job_id, None)


def _build_chunk_prompt(chunk_text: str, anchor_hint: str | None, running_summary: str) -> str:
    chronology_hint = f"Chronology anchor: {anchor_hint}\n" if anchor_hint else ""
    existing = running_summary or "No prior summary yet."
    return (
        "You are building a factual chronology digest. Preserve order and dates.\n"
        f"{chronology_hint}"
        f"Current running summary:\n{existing}\n\n"
        "New source chunk:\n"
        f"{chunk_text}\n\n"
        "Update the running summary with concise bullet-like prose that keeps chronology intact."
    )


def _build_final_prompt(running_summary: str) -> str:
    return (
        "Turn this running chronology summary into a concise final case digest. "
        "Keep the events in order, highlight key dates, and include unresolved gaps.\n\n"
        f"{running_summary}"
    )


def _merge_running_summary(current: str, addition: str) -> str:
    merged = "\n".join(part.strip() for part in [current, addition] if part and part.strip())
    return merged.strip()


def _serialize_job(db: Session, job_id: int) -> JobRead:
    job = db.scalar(select(Job).where(Job.id == job_id))
    running = db.scalar(
        select(Summary.content)
        .where(Summary.job_id == job_id, Summary.summary_type == "running")
        .order_by(Summary.created_at.desc(), Summary.id.desc())
        .limit(1)
    )
    final = db.scalar(
        select(Summary.content)
        .where(Summary.job_id == job_id, Summary.summary_type == "final")
        .order_by(Summary.created_at.desc(), Summary.id.desc())
        .limit(1)
    )
    payload = JobRead.model_validate(job, from_attributes=True)
    payload.running_summary = running
    payload.final_summary = final
    return payload
