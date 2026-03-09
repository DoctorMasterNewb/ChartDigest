from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseRead, CaseDetailRead
from app.schemas.document import DocumentRead
from app.schemas.job import JobCreate, JobRead
from app.schemas.provider import ProviderTestRequest, ProviderTestResponse
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.schemas.episode_state import EpisodeStateV2, EpisodeStateVersionCreate, EpisodeStateVersionRead
from app.services import case_service, document_service, episode_state_service, processing_service, settings_service

router = APIRouter(prefix="/api")


@router.get("")
def api_root() -> dict[str, str]:
    return {"name": "Chart Digest API", "status": "ok"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings", response_model=SettingsRead)
def get_settings_endpoint(db: Session = Depends(get_db)) -> SettingsRead:
    return settings_service.get_or_create_settings(db)


@router.put("/settings", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsRead:
    return settings_service.update_settings(db, payload)


@router.post("/providers/test", response_model=ProviderTestResponse)
async def test_provider(payload: ProviderTestRequest, db: Session = Depends(get_db)) -> ProviderTestResponse:
    settings = settings_service.resolve_provider_settings(db, payload.override_settings)
    return await processing_service.test_provider_connection(settings)


@router.get("/providers/ollama/models", response_model=list[str])
async def list_ollama_models(base_url: str | None = None, db: Session = Depends(get_db)) -> list[str]:
    settings = settings_service.get_or_create_settings(db)
    base = (base_url or settings.ollama_base_url).rstrip("/")
    url = f"{base}/api/tags"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to list Ollama models from {url}: {exc}") from exc

    models = payload.get("models", [])
    names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]
    return sorted(set(names))


@router.post("/cases", response_model=CaseRead)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseRead:
    return case_service.create_case(db, payload)


@router.get("/cases", response_model=list[CaseRead])
def list_cases(db: Session = Depends(get_db)) -> list[CaseRead]:
    return case_service.list_cases(db)


@router.get("/cases/{case_id}", response_model=CaseDetailRead)
def get_case(case_id: int, db: Session = Depends(get_db)) -> CaseDetailRead:
    case = case_service.get_case_detail(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case




@router.post("/cases/{case_id}/episode-state/versions", response_model=EpisodeStateVersionRead, status_code=201)
def create_episode_state_version(case_id: int, payload: EpisodeStateVersionCreate, db: Session = Depends(get_db)) -> EpisodeStateVersionRead:
    try:
        item = episode_state_service.create_episode_state_version(db, case_id, payload)
    except episode_state_service.EpisodeStateValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": "Invalid episode state", "errors": exc.errors}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return EpisodeStateVersionRead(
        id=item.id,
        case_id=item.case_id,
        version_number=item.version_number,
        canonical_state=EpisodeStateV2.model_validate(item.canonical_state_json),
        diff=item.diff_json,
        stability_score=item.stability_score,
        created_at=item.created_at,
    )


@router.get("/cases/{case_id}/episode-state", response_model=EpisodeStateVersionRead)
def get_latest_episode_state(case_id: int, db: Session = Depends(get_db)) -> EpisodeStateVersionRead:
    item = episode_state_service.get_latest_episode_state_version(db, case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Episode state not found")
    return EpisodeStateVersionRead(
        id=item.id,
        case_id=item.case_id,
        version_number=item.version_number,
        canonical_state=EpisodeStateV2.model_validate(item.canonical_state_json),
        diff=item.diff_json,
        stability_score=item.stability_score,
        created_at=item.created_at,
    )


@router.get("/cases/{case_id}/episode-state/versions", response_model=list[EpisodeStateVersionRead])
def list_episode_state_versions(case_id: int, db: Session = Depends(get_db)) -> list[EpisodeStateVersionRead]:
    items = episode_state_service.list_episode_state_versions(db, case_id)
    return [
        EpisodeStateVersionRead(
            id=item.id,
            case_id=item.case_id,
            version_number=item.version_number,
            canonical_state=EpisodeStateV2.model_validate(item.canonical_state_json),
            diff=item.diff_json,
            stability_score=item.stability_score,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.get("/cases/{case_id}/episode-state/versions/{version_number}", response_model=EpisodeStateVersionRead)
def get_episode_state_version(case_id: int, version_number: int, db: Session = Depends(get_db)) -> EpisodeStateVersionRead:
    item = episode_state_service.get_episode_state_version(db, case_id, version_number)
    if item is None:
        raise HTTPException(status_code=404, detail="Episode state version not found")
    return EpisodeStateVersionRead(
        id=item.id,
        case_id=item.case_id,
        version_number=item.version_number,
        canonical_state=EpisodeStateV2.model_validate(item.canonical_state_json),
        diff=item.diff_json,
        stability_score=item.stability_score,
        created_at=item.created_at,
    )


@router.post("/cases/{case_id}/documents", response_model=DocumentRead)
async def upload_document(case_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentRead:
    try:
        return await document_service.ingest_upload(db, case_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/cases/{case_id}/documents/{document_id}", status_code=204)
def delete_document(case_id: int, document_id: int, db: Session = Depends(get_db)) -> None:
    try:
        document_service.delete_document(db, case_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cases/{case_id}/process", response_model=JobRead)
async def start_processing(case_id: int, payload: JobCreate, db: Session = Depends(get_db)) -> JobRead:
    try:
        return await processing_service.start_case_processing(db, case_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobRead:
    job = processing_service.get_job_status(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
