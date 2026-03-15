from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.forecast_engine import generate_forecast
from app.core.db import get_session
from app.models import Forecast, Question


router = APIRouter(prefix="/questions", tags=["forecasts"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_get(obj: Any, *names: str, default: Any = None) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return default

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _question_to_dict(question: Any) -> dict[str, Any]:
    return {
        "id": _safe_get(question, "id"),
        "slug": _safe_get(question, "slug"),
        "title": _safe_get(question, "title"),
        "question": _safe_get(question, "question", "text"),
        "created_at": _safe_get(question, "created_at"),
        "resolved_at": _safe_get(question, "resolved_at"),
        "is_resolved": _safe_get(question, "is_resolved"),
        "outcome": _safe_get(question, "outcome"),
    }


def _forecast_model_to_summary_dict(forecast: Any) -> dict[str, Any]:
    return {
        "id": _safe_get(forecast, "id"),
        "question_id": _safe_get(forecast, "question_id"),
        "probability": _to_float(_safe_get(forecast, "probability")),
        "raw_probability": _to_float(_safe_get(forecast, "raw_probability")),
        "calibrated_probability": _to_float(_safe_get(forecast, "calibrated_probability")),
        "confidence": _to_float(_safe_get(forecast, "confidence")),
        "summary": _safe_get(forecast, "summary"),
        "explanation_md": _safe_get(forecast, "explanation_md"),
        "direct_answer": _safe_get(forecast, "direct_answer"),
        "answer_label": _safe_get(forecast, "answer_label"),
        "answer_confidence_band": _safe_get(forecast, "answer_confidence_band"),
        "answer_rationale_short": _safe_get(forecast, "answer_rationale_short"),
        "created_at": _safe_get(forecast, "created_at"),
        "updated_at": _safe_get(forecast, "updated_at"),
    }


def _extract_full_payload_from_forecast(forecast: Any) -> dict[str, Any]:
    return {
        "raw_probability": _to_float(_safe_get(forecast, "raw_probability")),
        "calibrated_probability": _to_float(_safe_get(forecast, "calibrated_probability")),
        "runtime_calibration_meta": _safe_get(forecast, "runtime_calibration_meta", default={}) or {},
        "calibration_signals": _safe_get(forecast, "calibration_signals", default={}) or {},
        "sources": _safe_get(forecast, "sources", default=[]) or [],
        "claims": _safe_get(forecast, "claims", default=[]) or [],
        "top_pro_claims": _safe_get(forecast, "top_pro_claims", default=[]) or [],
        "top_contra_claims": _safe_get(forecast, "top_contra_claims", default=[]) or [],
        "top_uncertainties": _safe_get(forecast, "top_uncertainties", default=[]) or [],
        "diagnostics": _safe_get(forecast, "diagnostics", default={}) or {},
        "direct_answer": _safe_get(forecast, "direct_answer"),
        "answer_label": _safe_get(forecast, "answer_label"),
        "answer_confidence_band": _safe_get(forecast, "answer_confidence_band"),
        "answer_rationale_short": _safe_get(forecast, "answer_rationale_short"),
    }


def _copy_engine_fields_onto_model(model: Any, payload: dict[str, Any]) -> None:
    field_names = [
        "probability",
        "raw_probability",
        "calibrated_probability",
        "confidence",
        "summary",
        "explanation_md",
        "runtime_calibration_meta",
        "calibration_signals",
        "sources",
        "claims",
        "top_pro_claims",
        "top_contra_claims",
        "top_uncertainties",
        "diagnostics",
        "direct_answer",
        "answer_label",
        "answer_confidence_band",
        "answer_rationale_short",
    ]

    for field_name in field_names:
        if hasattr(model, field_name) and field_name in payload:
            setattr(model, field_name, payload[field_name])


def _get_question_or_404(session: Session, question_id: int) -> Question:
    question = session.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


def _get_latest_forecast(session: Session, question_id: int) -> Forecast | None:
    statement = (
        select(Forecast)
        .where(Forecast.question_id == question_id)
        .order_by(Forecast.created_at.desc(), Forecast.id.desc())
    )
    return session.exec(statement).first()


@router.post("/{question_id}/forecast")
def create_forecast(question_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    question = _get_question_or_404(session, question_id)

    engine_payload = generate_forecast(question=question, session=session)

    forecast = Forecast(
        question_id=question_id,
        probability=engine_payload.get("probability"),
        raw_probability=engine_payload.get("raw_probability"),
        calibrated_probability=engine_payload.get("calibrated_probability"),
        confidence=engine_payload.get("confidence"),
        summary=engine_payload.get("summary"),
        explanation_md=engine_payload.get("explanation_md"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )

    _copy_engine_fields_onto_model(forecast, engine_payload)

    session.add(forecast)
    session.commit()
    session.refresh(forecast)

    return {
        "question": _question_to_dict(question),
        "forecast": _forecast_model_to_summary_dict(forecast),
    }


@router.get("/{question_id}/forecast/latest")
def get_latest_forecast_summary(
    question_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    question = _get_question_or_404(session, question_id)
    forecast = _get_latest_forecast(session, question_id)

    if forecast is None:
        raise HTTPException(status_code=404, detail="No forecast found for question")

    return {
        "question": _question_to_dict(question),
        "forecast": _forecast_model_to_summary_dict(forecast),
    }


@router.get("/{question_id}/forecast/latest/full")
def get_latest_forecast_full(
    question_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    question = _get_question_or_404(session, question_id)
    forecast = _get_latest_forecast(session, question_id)

    if forecast is None:
        raise HTTPException(status_code=404, detail="No forecast found for question")

    forecast_summary = _forecast_model_to_summary_dict(forecast)
    full_payload = _extract_full_payload_from_forecast(forecast)

    return {
        "question": _question_to_dict(question),
        "forecast": forecast_summary,
        "summary": _safe_get(forecast, "summary"),
        "sources": _to_list(full_payload.get("sources")),
        "claims": _to_list(full_payload.get("claims")),
        "top_pro_claims": _to_list(full_payload.get("top_pro_claims")),
        "top_contra_claims": _to_list(full_payload.get("top_contra_claims")),
        "top_uncertainties": _to_list(full_payload.get("top_uncertainties")),
        "diagnostics": full_payload.get("diagnostics") or {},
        "raw_probability": full_payload.get("raw_probability"),
        "calibrated_probability": full_payload.get("calibrated_probability"),
        "runtime_calibration_meta": full_payload.get("runtime_calibration_meta") or {},
        "calibration_signals": full_payload.get("calibration_signals") or {},
        "direct_answer": full_payload.get("direct_answer"),
        "answer_label": full_payload.get("answer_label"),
        "answer_confidence_band": full_payload.get("answer_confidence_band"),
        "answer_rationale_short": full_payload.get("answer_rationale_short"),
    }


@router.post("/{question_id}/forecast/recompute")
def recompute_latest_forecast(
    question_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    question = _get_question_or_404(session, question_id)

    engine_payload = generate_forecast(question=question, session=session)
    forecast = _get_latest_forecast(session, question_id)

    if forecast is None:
        forecast = Forecast(
            question_id=question_id,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(forecast)

    if hasattr(forecast, "updated_at"):
        setattr(forecast, "updated_at", _utcnow())

    if hasattr(forecast, "created_at") and _safe_get(forecast, "created_at") is None:
        setattr(forecast, "created_at", _utcnow())

    _copy_engine_fields_onto_model(forecast, engine_payload)

    if hasattr(forecast, "summary"):
        forecast.summary = engine_payload.get("summary")
    if hasattr(forecast, "explanation_md"):
        forecast.explanation_md = engine_payload.get("explanation_md")
    if hasattr(forecast, "probability"):
        forecast.probability = engine_payload.get("probability")
    if hasattr(forecast, "confidence"):
        forecast.confidence = engine_payload.get("confidence")

    session.commit()
    session.refresh(forecast)

    return {
        "question": _question_to_dict(question),
        "forecast": _forecast_model_to_summary_dict(forecast),
        "summary": _safe_get(forecast, "summary"),
        "sources": _to_list(_safe_get(forecast, "sources", default=[])),
        "claims": _to_list(_safe_get(forecast, "claims", default=[])),
        "top_pro_claims": _to_list(_safe_get(forecast, "top_pro_claims", default=[])),
        "top_contra_claims": _to_list(_safe_get(forecast, "top_contra_claims", default=[])),
        "top_uncertainties": _to_list(_safe_get(forecast, "top_uncertainties", default=[])),
        "diagnostics": _safe_get(forecast, "diagnostics", default={}) or {},
        "raw_probability": _to_float(_safe_get(forecast, "raw_probability")),
        "calibrated_probability": _to_float(_safe_get(forecast, "calibrated_probability")),
        "runtime_calibration_meta": _safe_get(forecast, "runtime_calibration_meta", default={}) or {},
        "calibration_signals": _safe_get(forecast, "calibration_signals", default={}) or {},
        "direct_answer": _safe_get(forecast, "direct_answer"),
        "answer_label": _safe_get(forecast, "answer_label"),
        "answer_confidence_band": _safe_get(forecast, "answer_confidence_band"),
        "answer_rationale_short": _safe_get(forecast, "answer_rationale_short"),
    }
