from typing import List
from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.forecast_engine import compute_probability
from app.models.question import Question
from app.models.evidence import EvidenceItem
from app.models.forecast import Forecast, ForecastRead


router = APIRouter(prefix="/questions", tags=["forecasts"])


def _build_question_text(question: Question) -> str:
    """
    Build a combined text blob from whatever fields exist on the Question model.
    Uses getattr so this stays robust even if some fields are absent.
    """
    parts = [
        getattr(question, "title", "") or "",
        getattr(question, "question", "") or "",
        getattr(question, "context", "") or "",
        getattr(question, "description", "") or "",
        getattr(question, "criteria", "") or "",
        getattr(question, "resolution_criteria", "") or "",
    ]
    return "\n".join(part for part in parts if part).strip()


@router.post("/{question_id}/forecast", response_model=ForecastRead)
def create_forecast(
    question_id: str,
    method_version: str = "v0.2.0",
    session: Session = Depends(get_session),
):
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    evidences = session.exec(
        select(EvidenceItem).where(EvidenceItem.question_id == question_id)
    ).all()

    question_text = _build_question_text(question)

    result = compute_probability(
        category=question.category,
        evidence=evidences,
        question_text=question_text,
    )

    inputs_hash = hashlib.sha256(
        (
            str(question_id)
            + "|"
            + str(question.category)
            + "|"
            + question_text
            + "|"
            + str([(e.id, e.direction, e.weight, e.indicator_type) for e in evidences])
        ).encode("utf-8")
    ).hexdigest()

    forecast = Forecast(
        question_id=question_id,
        probability=result["probability"],  # 0..1
        confidence=result["confidence"],    # 0..100
        method="bayes_logodds_v1",
        method_version=method_version,
        explanation_md=result["explanation_md"],
        inputs_hash=inputs_hash,
        created_at=datetime.utcnow(),
    )

    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    return forecast


@router.get("/{question_id}/forecasts", response_model=List[ForecastRead])
def get_forecasts(question_id: str, session: Session = Depends(get_session)):
    forecasts = session.exec(
        select(Forecast)
        .where(Forecast.question_id == question_id)
        .order_by(Forecast.created_at.desc())
    ).all()

    return forecasts
