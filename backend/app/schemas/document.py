from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: int
    case_id: int
    filename: str
    content_type: str | None
    extension: str
    status: str
    text_length: int
    created_at: datetime

    model_config = {"from_attributes": True}

