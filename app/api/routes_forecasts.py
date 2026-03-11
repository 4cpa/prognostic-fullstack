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


def _safe_text(value) -> str:
    return "" if value is None else str(value).strip()


def _build_question_text(question: Question) -> str:
    """
    Baut einen kombinierten Fragetext aus allen relevanten Feldern.
    Robuster Ansatz mit getattr, damit es nicht crasht, falls einzelne
    Felder im Modell fehlen.
    """
    parts = [
        _safe_text(getattr(question, "title", "")),
        _safe_text(getattr(question, "question", "")),
        _safe_text(getattr(question, "description", "")),
        _safe_text(getattr(question, "context", "")),
        _safe_text(getattr(question, "resolution_criteria", "")),
        _safe_text(getattr(question, "criteria", "")),
        _safe_text(getattr(question, "resolution_source_policy", "")),
        _safe_text(getattr(question, "region", "")),
        _safe_text(getattr(question, "country", "")),
        _safe_text(getattr(question, "resolve_at", "")),
    ]
    return "\n".join(part for part in parts if part)


def _build_inputs_hash(
    question: Question,
    evidences: List[EvidenceItem],
    method_version: str,
    question_text: str,
) -> str:
    evidence_payload = [
        {
            "id": str(getattr(e, "id", "")),
            "indicator_type": str(getattr(e, "indicator_type", "")),
            "direction": float(getattr(e, "direction", 0.0)),
            "weight": float(getattr(e, "weight", 0.0)),
        }
        for e in evidences
    ]

    raw = (
        f"question_id={getattr(question, 'id', '')}|"
        f"category={getattr(question, 'category', '')}|"
        f"method_version={method_version}|"
        f"question_text={question_text}|"
        f"evidences={evidence_payload}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("/{question_id}/forecast", response_model=ForecastRead)
def create_forecast(
    question_id: str,
    method_version: str = "v0.3.0",
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
        category=getattr(question, "category", "default"),
        evidence=evidences,
        question_text=question_text,
    )

    forecast = Forecast(
        question_id=question_id,
        probability=float(result["probability"]),   # 0..1
        confidence=float(result["confidence"]),     # 0..100
        method="bayes_logodds_v1",
        method_version=method_version,
        explanation_md=result["explanation_md"],
        inputs_hash=_build_inputs_hash(
            question=question,
            evidences=evidences,
            method_version=method_version,
            question_text=question_text,
        ),
        created_at=datetime.utcnow(),
    )

    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    return forecast


@router.get("/{question_id}/forecasts", response_model=List[ForecastRead])
def get_forecasts(question_id: str, session: Session = Depends(get_session)):
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    forecasts = session.exec(
        select(Forecast)
        .where(Forecast.question_id == question_id)
        .order_by(Forecast.created_at.desc())
    ).all()

    return forecasts


@router.get("/{question_id}/forecast/latest", response_model=ForecastRead)
def get_latest_forecast(question_id: str, session: Session = Depends(get_session)):
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    forecast = session.exec(
        select(Forecast)
        .where(Forecast.question_id == question_id)
        .order_by(Forecast.created_at.desc())
    ).first()

    if not forecast:
        raise HTTPException(status_code=404, detail="No forecast found for this question")

    return forecast
