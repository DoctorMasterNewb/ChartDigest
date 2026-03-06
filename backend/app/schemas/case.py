from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.document import DocumentRead
from app.schemas.job import JobRead


class CaseCreate(BaseModel):
    title: str
    description: str | None = None


class CaseRead(BaseModel):
    id: int
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseDetailRead(CaseRead):
    documents: list[DocumentRead]
    jobs: list[JobRead]
    running_summary: str | None = None
    final_summary: str | None = None

