from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.backtesting import run_backtest
from app.core.calibration import calibration_report
from app.models.forecast import Forecast
from app.models.question import Question


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _extract_outcome(question: Any) -> Optional[int]:
    candidate_fields = [
        "outcome",
        "resolved_outcome",
        "resolution_outcome",
        "is_true",
        "resolved_value",
    ]

    raw = None
    for field in candidate_fields:
        if hasattr(question, field):
            raw = getattr(question, field)
            if raw is not None:
                break

    if raw is None:
        return None

    if isinstance(raw, bool):
        return 1 if raw else 0

    if isinstance(raw, int):
        return 1 if raw >= 1 else 0

    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "y", "resolved_yes", "positive"}:
        return 1
    if text in {"0", "false", "no", "n", "resolved_no", "negative"}:
        return 0

    return None


def _is_resolved(question: Any) -> bool:
    candidate_fields = [
        "is_resolved",
        "resolved",
        "is_closed",
        "closed",
    ]

    for field in candidate_fields:
        if hasattr(question, field):
            value = getattr(question, field)
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return value == 1
            if isinstance(value, str):
                text = value.strip().lower()
                if text in {"true", "1", "yes", "resolved", "closed"}:
                    return True
                if text in {"false", "0", "no", "open"}:
                    return False

    return _extract_outcome(question) is not None


def _resolved_questions(session: Session) -> List[Question]:
    questions = session.exec(select(Question)).all()
    return [q for q in questions if _is_resolved(q)]


def _forecasts_for_questions(session: Session, question_ids: List[str]) -> Dict[str, List[Forecast]]:
    if not question_ids:
        return {}

    forecasts = session.exec(
        select(Forecast).where(Forecast.question_id.in_(question_ids))
    ).all()

    grouped: Dict[str, List[Forecast]] = {}
    for forecast in forecasts:
        grouped.setdefault(_safe_str(forecast.question_id), []).append(forecast)

    return grouped


def load_backtest_summary(
    session: Session,
) -> Dict[str, Any]:
    questions = _resolved_questions(session)
    question_ids = [_safe_str(q.id) for q in questions if _safe_str(q.id)]
    forecasts_by_question = _forecasts_for_questions(session, question_ids)

    return run_backtest(
        questions=questions,
        forecasts_by_question=forecasts_by_question,
    )


def load_calibration_report(
    session: Session,
    *,
    num_bins: int = 10,
    min_bin_count: int = 3,
) -> Dict[str, Any]:
    summary = load_backtest_summary(session)

    report = calibration_report(
        summary,
        num_bins=num_bins,
        min_bin_count=min_bin_count,
    )

    return {
        "backtest_summary": summary,
        "calibration_report": report,
    }


def load_runtime_calibration(
    session: Session,
    *,
    num_bins: int = 10,
    min_bin_count: int = 3,
) -> Dict[str, Any]:
    """
    Returns the calibration payload used at runtime by the forecast engine.

    Shape:
    {
      "global": {...},
      "by_category": {...},
      "meta": {...}
    }
    """
    payload = load_calibration_report(
        session,
        num_bins=num_bins,
        min_bin_count=min_bin_count,
    )

    backtest_summary = payload.get("backtest_summary", {}) or {}
    calibration_payload = payload.get("calibration_report", {}) or {}

    global_table = calibration_payload.get("global", {}) or {}
    by_category = calibration_payload.get("by_category", {}) or {}

    return {
        "global": global_table,
        "by_category": by_category,
        "meta": {
            "record_count": int(backtest_summary.get("count", 0) or 0),
            "num_bins": int(global_table.get("num_bins", num_bins) or num_bins),
            "min_bin_count": int(global_table.get("min_bin_count", min_bin_count) or min_bin_count),
            "overall_brier_score": float(
                ((backtest_summary.get("overall", {}) or {}).get("brier_score", 0.0)) or 0.0
            ),
            "overall_mae": float(
                ((backtest_summary.get("overall", {}) or {}).get("mae", 0.0)) or 0.0
            ),
            "overall_rmse": float(
                ((backtest_summary.get("overall", {}) or {}).get("rmse", 0.0)) or 0.0
            ),
        },
    }


def select_calibration_table_for_category(
    runtime_calibration: Dict[str, Any],
    category: Optional[str],
) -> Dict[str, Any]:
    """
    Prefers category-specific calibration if present and populated.
    Falls back to the global calibration table.
    """
    category_name = _safe_str(category, "default") or "default"

    by_category = runtime_calibration.get("by_category", {}) or {}
    category_tables = by_category.get("tables", {}) or {}
    category_table = category_tables.get(category_name)

    if category_table and int(category_table.get("count", 0) or 0) > 0:
        return category_table

    return runtime_calibration.get("global", {}) or {}
