from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseRead, CaseDetailRead
from app.schemas.document import DocumentRead
from app.schemas.job import JobCreate, JobRead
from app.schemas.provider import ProviderTestRequest, ProviderTestResponse
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services import case_service, document_service, processing_service, settings_service

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
