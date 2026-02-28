from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
import uuid

from sqlmodel import Session
from app.core.db import get_session
from app.models import Question, QuestionStatus

router = APIRouter(prefix="/questions", tags=["questions"])

@router.post("", response_model=Question)
def create_question(payload: Question, session: Session = Depends(get_session)):
    q = payload
    q.id = q.id or str(uuid.uuid4())
    q.created_at = datetime.utcnow()
    q.status = QuestionStatus.open
    session.add(q)
    session.commit()
    session.refresh(q)
    return q

@router.get("/{question_id}", response_model=Question)
def get_question(question_id: str, session: Session = Depends(get_session)):
    q = session.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q

@router.post("/{question_id}/resolve", response_model=Question)
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
