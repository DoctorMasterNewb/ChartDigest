from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.case import Case
from app.models.summary import Summary
from app.schemas.case import CaseCreate


def create_case(db: Session, payload: CaseCreate) -> Case:
    case = Case(title=payload.title.strip(), description=payload.description)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session) -> list[Case]:
    return list(db.scalars(select(Case).order_by(Case.created_at.desc())))


def get_case_detail(db: Session, case_id: int) -> Case | None:
    case = db.scalar(
        select(Case)
        .options(selectinload(Case.documents), selectinload(Case.jobs), selectinload(Case.summaries))
        .where(Case.id == case_id)
    )
    if case is None:
        return None

    case.documents.sort(key=lambda item: item.created_at, reverse=True)
    case.jobs.sort(key=lambda item: item.created_at, reverse=True)
    running = next((summary.content for summary in reversed(case.summaries) if summary.summary_type == "running"), None)
    final = next((summary.content for summary in reversed(case.summaries) if summary.summary_type == "final"), None)
    setattr(case, "running_summary", running)
    setattr(case, "final_summary", final)
    return case
