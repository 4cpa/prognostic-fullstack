from typing import List, Dict, Any
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


def _serialize_forecast(forecast: Forecast) -> Dict[str, Any]:
    return {
        "id": forecast.id,
        "question_id": forecast.question_id,
        "created_at": forecast.created_at.isoformat() if forecast.created_at else None,
        "probability": forecast.probability,
        "confidence": forecast.confidence,
        "method": forecast.method,
        "method_version": forecast.method_version,
        "explanation_md": forecast.explanation_md,
        "inputs_hash": forecast.inputs_hash,
    }


def _serialize_source(source: ForecastSource) -> Dict[str, Any]:
    return {
        "id": source.id,
        "forecast_id": source.forecast_id,
        "url": source.url,
        "title": source.title,
        "publisher": source.publisher,
        "domain": source.domain,
        "source_type": source.source_type,
        "published_at": source.published_at,
        "query": source.query,
        "retrieval_method": source.retrieval_method,
        "relevance_score": source.relevance_score,
        "credibility_score": source.credibility_score,
        "freshness_score": source.freshness_score,
        "overall_score": source.overall_score,
        "stance": source.stance,
        "signal_strength": source.signal_strength,
        "summary": source.summary,
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }


def _serialize_claim(claim: ForecastClaim) -> Dict[str, Any]:
    return {
        "id": claim.id,
        "forecast_id": claim.forecast_id,
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "source_url": claim.source_url,
        "source_title": claim.source_title,
        "source_type": claim.source_type,
        "claim_confidence": claim.claim_confidence,
        "time_relevance": claim.time_relevance,
        "source_quality_weight": claim.source_quality_weight,
        "claim_confidence_weight": claim.claim_confidence_weight,
        "time_relevance_weight": claim.time_relevance_weight,
        "relevance_weight": claim.relevance_weight,
        "freshness_weight": claim.freshness_weight,
        "independence_weight": claim.independence_weight,
        "specificity_weight": claim.specificity_weight,
        "support_boost": claim.support_boost,
        "final_weight": claim.final_weight,
        "direction": claim.direction,
        "signed_weight": claim.signed_weight,
        "supporting_source_count": claim.supporting_source_count,
        "supporting_domain_count": claim.supporting_domain_count,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
    }


def _bucket_claims(claims: List[ForecastClaim], limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    scored = sorted(
        claims,
        key=lambda c: (
            float(c.final_weight or 0.0),
            float(c.claim_confidence or 0.0),
            float(c.time_relevance or 0.0),
        ),
        reverse=True,
    )

    def pick(claim_type: str) -> List[Dict[str, Any]]:
        return [_serialize_claim(c) for c in scored if c.claim_type == claim_type][:limit]

    return {
        "top_pro_claims": pick("pro"),
        "top_contra_claims": pick("contra"),
        "top_uncertainties": pick("uncertainty"),
        "top_background": pick("background"),
    }


def _extract_summary_from_explanation(explanation_md: str) -> str:
    if not explanation_md:
        return ""

    marker = "### Kurzbegründung"
    start = explanation_md.find(marker)
    if start == -1:
        return ""

    rest = explanation_md[start + len(marker):].strip()
    next_header = rest.find("### ")
    if next_header != -1:
        rest = rest[:next_header].strip()

    return rest.strip()


@router.post("/{question_id}/forecast", response_model=ForecastRead)
def create_forecast(
    question_id: str,
    method_version: str = "v0.5.0",
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
        session=session,
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


@router.get("/{question_id}/forecast/latest/full")
def get_latest_forecast_full(question_id: str, session: Session = Depends(get_session)):
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

    sources = session.exec(
        select(ForecastSource)
        .where(ForecastSource.forecast_id == forecast.id)
        .order_by(ForecastSource.overall_score.desc(), ForecastSource.created_at.desc())
    ).all()

    claims = session.exec(
        select(ForecastClaim)
        .where(ForecastClaim.forecast_id == forecast.id)
        .order_by(ForecastClaim.final_weight.desc(), ForecastClaim.created_at.desc())
    ).all()

    source_counts = {
        "official": sum(1 for s in sources if s.source_type == "official"),
        "wire": sum(1 for s in sources if s.source_type == "wire"),
        "research": sum(1 for s in sources if s.source_type == "research"),
        "major_media": sum(1 for s in sources if s.source_type == "major_media"),
        "other": sum(1 for s in sources if s.source_type == "other"),
    }

    claim_counts = {
        "pro": sum(1 for c in claims if c.claim_type == "pro"),
        "contra": sum(1 for c in claims if c.claim_type == "contra"),
        "uncertainty": sum(1 for c in claims if c.claim_type == "uncertainty"),
        "background": sum(1 for c in claims if c.claim_type == "background"),
    }

    buckets = _bucket_claims(claims, limit=5)

    diagnostics = {
        "source_count": len(sources),
        "claim_count": len(claims),
        "source_counts": source_counts,
        "claim_counts": claim_counts,
        "pro_weight_sum": round(sum(float(c.final_weight or 0.0) for c in claims if c.claim_type == "pro"), 4),
        "contra_weight_sum": round(sum(float(c.final_weight or 0.0) for c in claims if c.claim_type == "contra"), 4),
        "uncertainty_weight_sum": round(sum(float(c.final_weight or 0.0) for c in claims if c.claim_type == "uncertainty"), 4),
        "background_weight_sum": round(sum(float(c.final_weight or 0.0) for c in claims if c.claim_type == "background"), 4),
        "net_signal": round(sum(float(c.signed_weight or 0.0) for c in claims), 4),
    }

    return {
        "question": {
            "id": getattr(question, "id", None),
            "title": getattr(question, "title", None),
            "category": getattr(question, "category", None),
            "resolve_at": getattr(question, "resolve_at", None),
            "resolution_criteria": getattr(question, "resolution_criteria", None),
            "resolution_source_policy": getattr(question, "resolution_source_policy", None),
        },
        "forecast": _serialize_forecast(forecast),
        "summary": _extract_summary_from_explanation(forecast.explanation_md),
        "sources": [_serialize_source(s) for s in sources],
        "claims": [_serialize_claim(c) for c in claims],
        "source_counts": source_counts,
        "claim_counts": claim_counts,
        "diagnostics": diagnostics,
        **buckets,
    }
