from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.case import Case
from app.models.document import Document

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


async def ingest_upload(db: Session, case_id: int, upload: UploadFile) -> Document:
    case = db.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise ValueError("Case not found")

    extension = Path(upload.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .txt, .md, and text-based .pdf files are supported")

    settings = get_settings()
    token = uuid4().hex
    upload_path = Path(settings.uploads_dir) / f"{token}{extension}"
    text_path = Path(settings.extracted_dir) / f"{token}.txt"

    raw_bytes = await upload.read()
    upload_path.write_bytes(raw_bytes)

    extracted_text = _extract_text(upload_path, extension)
    normalized_text = _normalize_text(extracted_text)
    if not normalized_text.strip():
        raise ValueError("No extractable text found in the uploaded file")

    text_path.write_text(normalized_text, encoding="utf-8")
    metadata = {"original_filename": upload.filename}

    document = Document(
        case_id=case_id,
        filename=upload.filename or upload_path.name,
        content_type=upload.content_type,
        extension=extension,
        status="ingested",
        file_path=str(upload_path),
        text_path=str(text_path),
        text_length=len(normalized_text),
        metadata_json=json.dumps(metadata),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def load_document_text(document: Document) -> str:
    return Path(document.text_path).read_text(encoding="utf-8")


def _extract_text(path: Path, extension: str) -> str:
    if extension in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if extension == ".pdf":
        reader = PdfReader(str(path))
        return "\n\n".join(filter(None, (page.extract_text() for page in reader.pages)))
    raise ValueError("Unsupported file type")


def _normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip() + "\n"

