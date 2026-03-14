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
from app.models.forecast_source import ForecastSource
from app.models.forecast_claim import ForecastClaim


router = APIRouter(prefix="/questions", tags=["forecasts"])


def _safe_text(value) -> str:
    return "" if value is None else str(value).strip()


def _build_question_text(question: Question) -> str:
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


def _persist_sources(session: Session, forecast_id: str, sources: List[dict]) -> None:
    for source in sources:
        record = ForecastSource(
            forecast_id=forecast_id,
            url=_safe_text(source.get("url", "")),
            title=_safe_text(source.get("title", "")),
            publisher=_safe_text(source.get("publisher", "")),
            domain=_safe_text(source.get("domain", "")) or None,
            source_type=_safe_text(source.get("source_type", "other")) or "other",
            published_at=_safe_text(source.get("published_at", "")) or None,
            query=_safe_text(source.get("query", "")) or None,
            retrieval_method=_safe_text(source.get("retrieval_method", "")) or None,
            relevance_score=float(source.get("relevance_score", 0.0) or 0.0),
            credibility_score=float(source.get("credibility_score", 0.0) or 0.0),
            freshness_score=float(source.get("freshness_score", 0.0) or 0.0),
            overall_score=float(source.get("overall_score", 0.0) or 0.0),
            stance=_safe_text(source.get("stance", "neutral")) or "neutral",
            signal_strength=float(source.get("signal_strength", 0.0) or 0.0),
            summary=_safe_text(source.get("summary", "")) or None,
        )
        session.add(record)


def _persist_claims(session: Session, forecast_id: str, claims: List[dict]) -> None:
    for claim in claims:
        record = ForecastClaim(
            forecast_id=forecast_id,
            claim_text=_safe_text(claim.get("claim_text", "")),
            claim_type=_safe_text(claim.get("claim_type", "background")) or "background",
            source_url=_safe_text(claim.get("source_url", "")),
            source_title=_safe_text(claim.get("source_title", "")),
            source_type=_safe_text(claim.get("source_type", "other")) or "other",
            claim_confidence=float(claim.get("claim_confidence", 0.0) or 0.0),
            time_relevance=float(claim.get("time_relevance", 0.0) or 0.0),
            source_quality_weight=(
                float(claim.get("source_quality_weight"))
                if claim.get("source_quality_weight") is not None
                else None
            ),
            claim_confidence_weight=(
                float(claim.get("claim_confidence_weight"))
                if claim.get("claim_confidence_weight") is not None
                else None
            ),
            time_relevance_weight=(
                float(claim.get("time_relevance_weight"))
                if claim.get("time_relevance_weight") is not None
                else None
            ),
            relevance_weight=(
                float(claim.get("relevance_weight"))
                if claim.get("relevance_weight") is not None
                else None
            ),
            freshness_weight=(
                float(claim.get("freshness_weight"))
                if claim.get("freshness_weight") is not None
                else None
            ),
            independence_weight=(
                float(claim.get("independence_weight"))
                if claim.get("independence_weight") is not None
                else None
            ),
            specificity_weight=(
                float(claim.get("specificity_weight"))
                if claim.get("specificity_weight") is not None
                else None
            ),
            support_boost=(
                float(claim.get("support_boost"))
                if claim.get("support_boost") is not None
                else None
            ),
            final_weight=(
                float(claim.get("final_weight"))
                if claim.get("final_weight") is not None
                else None
            ),
            direction=(
                int(claim.get("direction"))
                if claim.get("direction") is not None
                else 0
            ),
            signed_weight=(
                float(claim.get("signed_weight"))
                if claim.get("signed_weight") is not None
                else None
            ),
            supporting_source_count=(
                int(claim.get("supporting_source_count"))
                if claim.get("supporting_source_count") is not None
                else 1
            ),
            supporting_domain_count=(
                int(claim.get("supporting_domain_count"))
                if claim.get("supporting_domain_count") is not None
                else 1
            ),
        )
        session.add(record)


@router.post("/{question_id}/forecast", response_model=ForecastRead)
def create_forecast(
    question_id: str,
    method_version: str = "v0.4.0",
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
        probability=float(result["probability"]),
        confidence=float(result["confidence"]),
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

    _persist_sources(
        session=session,
        forecast_id=forecast.id,
        sources=result.get("sources", []) or [],
    )
    _persist_claims(
        session=session,
        forecast_id=forecast.id,
        claims=result.get("scored_claims", []) or [],
    )

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
