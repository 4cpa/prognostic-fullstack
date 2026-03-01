from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.question import Question, QuestionStatus, QuestionCreate, QuestionRead
from app.models.evidence import EvidenceItem, EvidenceCreate, EvidenceRead

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", response_model=QuestionRead)
def create_question(payload: QuestionCreate, session: Session = Depends(get_session)):
    q = Question(
        id=str(uuid.uuid4()),
        title=payload.title,
        description=payload.description,
        category=payload.category,
        region=payload.region,
        country=payload.country,
        created_at=datetime.utcnow(),
        resolve_at=payload.resolve_at,
        resolution_criteria=payload.resolution_criteria,
        resolution_source_policy=payload.resolution_source_policy,
        status=QuestionStatus.open,
    )
    session.add(q)
    session.commit()
    session.refresh(q)
    return q


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: str, session: Session = Depends(get_session)):
    q = session.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.post("/{question_id}/evidence", response_model=EvidenceRead)
def add_evidence(
    question_id: str,
    payload: EvidenceCreate,
    session: Session = Depends(get_session),
):
    q = session.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    ev = EvidenceItem(
        id=str(uuid.uuid4()),
        question_id=question_id,
        created_at=datetime.utcnow(),
        indicator_type=payload.indicator_type,
        direction=payload.direction,
        weight=payload.weight,
        note=payload.note,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


@router.get("/{question_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(question_id: str, session: Session = Depends(get_session)):
    # Python 3.10 im Container ok: list[EvidenceRead]
    q = session.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    items = session.exec(
        select(EvidenceItem)
        .where(EvidenceItem.question_id == question_id)
        .order_by(EvidenceItem.created_at.desc())
    ).all()
    return items


@router.post("/{question_id}/resolve", response_model=QuestionRead)
def resolve_question(
    question_id: str,
    outcome: str,  # yes|no|void
    resolved_by: Optional[str] = None,
    notes: Optional[str] = None,
    session: Session = Depends(get_session),
):
    q = session.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if outcome not in {"yes", "no", "void"}:
        raise HTTPException(status_code=400, detail="outcome must be yes|no|void")

    q.resolved_at = datetime.utcnow()
    q.resolved_by = resolved_by
    q.resolution_notes = notes

    if outcome == "yes":
        q.status = QuestionStatus.resolved_yes
    elif outcome == "no":
        q.status = QuestionStatus.resolved_no
    else:
        q.status = QuestionStatus.void

    session.add(q)
    session.commit()
    session.refresh(q)
    return q
