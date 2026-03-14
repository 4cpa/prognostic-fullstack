from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from math import sqrt
from typing import Any, Dict, List, Optional


@dataclass
class BacktestRecord:
    question_id: str
    question_title: str
    category: str
    resolve_at: Optional[str]
    outcome: int
    forecast_id: str
    forecast_created_at: str
    probability: float
    confidence: float
    method: str
    method_version: str
    horizon_days: Optional[float]
    brier_component: float
    absolute_error: float
    squared_error: float


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _clamp_probability(p: Any) -> float:
    try:
        value = float(p)
    except Exception:
        value = 0.5

    # defensive normalization for legacy 0..100 rows
    if value > 1.0:
        value = value / 100.0

    return min(max(value, 0.0), 1.0)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _extract_outcome(question: Any) -> Optional[int]:
    """
    Tries several common field names.
    Accepted truthy/falsey values:
    - bool
    - int 0/1
    - strings like yes/no, true/false, resolved_yes/resolved_no
    """
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
    """
    Tries several common field names to determine whether a question is resolved.
    """
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

    # fallback: if an explicit outcome exists, treat as resolved
    return _extract_outcome(question) is not None


def _question_resolve_at(question: Any) -> Optional[datetime]:
    candidate_fields = [
        "resolved_at",
        "resolve_at",
        "resolution_date",
        "closed_at",
    ]
    for field in candidate_fields:
        if hasattr(question, field):
            dt = _parse_dt(getattr(question, field))
            if dt is not None:
                return dt
    return None


def _pick_latest_forecast_before_resolution(
    forecasts: List[Any],
    resolve_at: Optional[datetime],
) -> Optional[Any]:
    """
    Picks the latest forecast whose created_at <= resolve_at.
    If resolve_at is missing, picks the latest forecast overall.
    """
    if not forecasts:
        return None

    enriched = []
    for f in forecasts:
        created_at = _parse_dt(getattr(f, "created_at", None))
        enriched.append((f, created_at))

    valid = [(f, dt) for f, dt in enriched if dt is not None]

    if not valid:
        return None

    if resolve_at is None:
        valid.sort(key=lambda item: item[1], reverse=True)
        return valid[0][0]

    candidates = [(f, dt) for f, dt in valid if dt <= resolve_at]
    if candidates:
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates[0][0]

    # fallback: if all forecasts are after resolution, take earliest one
    valid.sort(key=lambda item: item[1])
    return valid[0][0]


def _compute_horizon_days(forecast_created_at: Optional[datetime], resolve_at: Optional[datetime]) -> Optional[float]:
    if forecast_created_at is None or resolve_at is None:
        return None
    delta = resolve_at - forecast_created_at
    return round(delta.total_seconds() / 86400.0, 2)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _bucket_probability(p: float) -> str:
    lower = int(p * 10) * 10
    upper = min(lower + 10, 100)
    if lower == 100:
        lower = 90
        upper = 100
    return f"{lower:02d}-{upper:02d}%"


def build_backtest_records(
    questions: List[Any],
    forecasts_by_question: Dict[str, List[Any]],
) -> List[BacktestRecord]:
    records: List[BacktestRecord] = []

    for question in questions:
        question_id = _safe_str(getattr(question, "id", ""))
        if not question_id:
            continue

        if not _is_resolved(question):
            continue

        outcome = _extract_outcome(question)
        if outcome is None:
            continue

        resolve_at = _question_resolve_at(question)
        forecasts = forecasts_by_question.get(question_id, []) or []
        selected = _pick_latest_forecast_before_resolution(forecasts, resolve_at)

        if selected is None:
            continue

        p = _clamp_probability(getattr(selected, "probability", 0.5))
        conf = _safe_float(getattr(selected, "confidence", 0.0), 0.0)
        created_at = _parse_dt(getattr(selected, "created_at", None))
        horizon_days = _compute_horizon_days(created_at, resolve_at)

        brier_component = (p - outcome) ** 2
        absolute_error = abs(p - outcome)
        squared_error = brier_component

        records.append(
            BacktestRecord(
                question_id=question_id,
                question_title=_safe_str(getattr(question, "title", "")),
                category=_safe_str(getattr(question, "category", "default"), "default"),
                resolve_at=resolve_at.isoformat() if resolve_at else None,
                outcome=int(outcome),
                forecast_id=_safe_str(getattr(selected, "id", "")),
                forecast_created_at=created_at.isoformat() if created_at else "",
                probability=round(p, 4),
                confidence=round(conf, 2),
                method=_safe_str(getattr(selected, "method", "")),
                method_version=_safe_str(getattr(selected, "method_version", "")),
                horizon_days=horizon_days,
                brier_component=round(brier_component, 6),
                absolute_error=round(absolute_error, 6),
                squared_error=round(squared_error, 6),
            )
        )

    return records


def _aggregate_group(records: List[BacktestRecord]) -> Dict[str, Any]:
    if not records:
        return {
            "count": 0,
            "brier_score": 0.0,
            "mae": 0.0,
            "rmse": 0.0,
            "avg_probability": 0.0,
            "avg_outcome": 0.0,
            "avg_confidence": 0.0,
            "avg_horizon_days": None,
        }

    brier_values = [r.brier_component for r in records]
    abs_values = [r.absolute_error for r in records]
    probs = [r.probability for r in records]
    outcomes = [float(r.outcome) for r in records]
    confidences = [r.confidence for r in records]
    horizons = [r.horizon_days for r in records if r.horizon_days is not None]

    brier = _mean(brier_values)
    mae = _mean(abs_values)
    rmse = sqrt(_mean(brier_values))

    return {
        "count": len(records),
        "brier_score": round(brier, 6),
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "avg_probability": round(_mean(probs), 6),
        "avg_outcome": round(_mean(outcomes), 6),
        "avg_confidence": round(_mean(confidences), 6),
        "avg_horizon_days": round(_mean(horizons), 2) if horizons else None,
    }


def _reliability_bins(records: List[BacktestRecord]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[BacktestRecord]] = defaultdict(list)

    for record in records:
        bucket = _bucket_probability(record.probability)
        buckets[bucket].append(record)

    def bucket_sort_key(name: str) -> int:
        try:
            return int(name.split("-")[0])
        except Exception:
            return 999

    result: List[Dict[str, Any]] = []

    for bucket_name in sorted(buckets.keys(), key=bucket_sort_key):
        group = buckets[bucket_name]
        avg_pred = _mean([r.probability for r in group])
        avg_outcome = _mean([float(r.outcome) for r in group])

        result.append(
            {
                "bucket": bucket_name,
                "count": len(group),
                "avg_predicted": round(avg_pred, 6),
                "avg_observed": round(avg_outcome, 6),
                "gap": round(avg_pred - avg_outcome, 6),
            }
        )

    return result


def summarize_backtest(
    records: List[BacktestRecord],
) -> Dict[str, Any]:
    by_category: Dict[str, List[BacktestRecord]] = defaultdict(list)
    by_method_version: Dict[str, List[BacktestRecord]] = defaultdict(list)

    for record in records:
        by_category[record.category].append(record)
        by_method_version[record.method_version].append(record)

    category_summary = {
        category: _aggregate_group(group)
        for category, group in sorted(by_category.items(), key=lambda item: item[0])
    }

    method_version_summary = {
        version: _aggregate_group(group)
        for version, group in sorted(by_method_version.items(), key=lambda item: item[0])
    }

    return {
        "count": len(records),
        "overall": _aggregate_group(records),
        "reliability_bins": _reliability_bins(records),
        "by_category": category_summary,
        "by_method_version": method_version_summary,
        "records": [asdict(r) for r in records],
    }


def run_backtest(
    questions: List[Any],
    forecasts_by_question: Dict[str, List[Any]],
) -> Dict[str, Any]:
    """
    Main helper for application code.

    Expected inputs:
    - questions: iterable of resolved/open question objects
    - forecasts_by_question: dict[question_id] -> list of forecast objects

    Each question should ideally expose:
    - id
    - title
    - category
    - resolve_at / resolved_at
    - is_resolved / resolved
    - outcome / resolved_outcome

    Each forecast should ideally expose:
    - id
    - question_id
    - created_at
    - probability
    - confidence
    - method
    - method_version
    """
    records = build_backtest_records(questions, forecasts_by_question)
    return summarize_backtest(records)
