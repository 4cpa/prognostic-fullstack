from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class CalibrationBin:
    bucket: str
    lower: float
    upper: float
    count: int
    avg_predicted: float
    avg_observed: float
    correction: float


def _clamp_probability(p: Any) -> float:
    try:
        value = float(p)
    except Exception:
        value = 0.5

    # defensive normalization for legacy 0..100 values
    if value > 1.0:
        value = value / 100.0

    return min(max(value, 0.0), 1.0)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _bucket_bounds(num_bins: int) -> List[tuple]:
    if num_bins <= 0:
        num_bins = 10

    step = 1.0 / num_bins
    bounds = []
    start = 0.0

    for i in range(num_bins):
        end = start + step
        if i == num_bins - 1:
            end = 1.0
        bounds.append((round(start, 10), round(end, 10)))
        start = end

    return bounds


def _bucket_name(lower: float, upper: float) -> str:
    return f"{int(round(lower * 100)):02d}-{int(round(upper * 100)):02d}%"


def _find_bucket_index(p: float, num_bins: int) -> int:
    if p >= 1.0:
        return num_bins - 1
    idx = int(p * num_bins)
    return min(max(idx, 0), num_bins - 1)


def build_calibration_table(
    backtest_records: List[Dict[str, Any]],
    *,
    num_bins: int = 10,
    min_bin_count: int = 3,
) -> Dict[str, Any]:
    """
    Builds a simple bucket-based calibration table from backtest records.

    Expected record fields:
    - probability (0..1 or legacy 0..100)
    - outcome (0/1)
    """
    bounds = _bucket_bounds(num_bins)
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(num_bins)]

    for record in backtest_records:
        p = _clamp_probability(record.get("probability", 0.5))
        idx = _find_bucket_index(p, num_bins)
        buckets[idx].append(
            {
                "probability": p,
                "outcome": 1.0 if int(record.get("outcome", 0)) == 1 else 0.0,
            }
        )

    calibration_bins: List[CalibrationBin] = []

    for idx, records in enumerate(buckets):
        lower, upper = bounds[idx]
        avg_predicted = _mean([r["probability"] for r in records]) if records else (lower + upper) / 2.0
        avg_observed = _mean([r["outcome"] for r in records]) if records else avg_predicted

        if len(records) >= min_bin_count:
            correction = avg_observed - avg_predicted
        else:
            correction = 0.0

        calibration_bins.append(
            CalibrationBin(
                bucket=_bucket_name(lower, upper),
                lower=round(lower, 6),
                upper=round(upper, 6),
                count=len(records),
                avg_predicted=round(avg_predicted, 6),
                avg_observed=round(avg_observed, 6),
                correction=round(correction, 6),
            )
        )

    overall_count = sum(b.count for b in calibration_bins)
    avg_abs_gap = _mean([abs(b.correction) for b in calibration_bins if b.count > 0])

    return {
        "num_bins": num_bins,
        "min_bin_count": min_bin_count,
        "count": overall_count,
        "avg_abs_gap": round(avg_abs_gap, 6),
        "bins": [asdict(b) for b in calibration_bins],
    }


def calibrate_probability(
    raw_probability: float,
    calibration_table: Dict[str, Any],
) -> float:
    """
    Applies simple bucket-based calibration:
    calibrated = raw + bucket_correction

    If the bucket has too little data, correction will normally be 0.0.
    """
    p = _clamp_probability(raw_probability)

    bins = calibration_table.get("bins", []) or []
    if not bins:
        return round(p, 6)

    chosen_bin: Optional[Dict[str, Any]] = None

    for bucket in bins:
        lower = float(bucket.get("lower", 0.0))
        upper = float(bucket.get("upper", 1.0))

        if lower <= p < upper:
            chosen_bin = bucket
            break

        # include exact 1.0 in final bucket
        if p == 1.0 and upper == 1.0:
            chosen_bin = bucket
            break

    if chosen_bin is None:
        return round(p, 6)

    correction = float(chosen_bin.get("correction", 0.0))
    calibrated = min(max(p + correction, 0.0), 1.0)
    return round(calibrated, 6)


def calibration_diagnostics(
    calibration_table: Dict[str, Any],
) -> Dict[str, Any]:
    bins = calibration_table.get("bins", []) or []
    populated = [b for b in bins if int(b.get("count", 0)) > 0]

    if not populated:
        return {
            "count_populated_bins": 0,
            "count_empty_bins": len(bins),
            "max_abs_correction": 0.0,
            "mean_abs_correction": 0.0,
        }

    abs_corrections = [abs(float(b.get("correction", 0.0))) for b in populated]

    return {
        "count_populated_bins": len(populated),
        "count_empty_bins": len(bins) - len(populated),
        "max_abs_correction": round(max(abs_corrections), 6),
        "mean_abs_correction": round(_mean(abs_corrections), 6),
    }


def build_category_calibration_tables(
    backtest_records: List[Dict[str, Any]],
    *,
    num_bins: int = 10,
    min_bin_count: int = 3,
) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for record in backtest_records:
        category = str(record.get("category", "default") or "default").strip() or "default"
        grouped.setdefault(category, []).append(record)

    tables = {
        category: build_calibration_table(
            records,
            num_bins=num_bins,
            min_bin_count=min_bin_count,
        )
        for category, records in sorted(grouped.items(), key=lambda item: item[0])
    }

    return {
        "count_categories": len(tables),
        "tables": tables,
    }


def calibrate_probability_for_category(
    raw_probability: float,
    category: Optional[str],
    global_calibration_table: Dict[str, Any],
    category_calibration_tables: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Prefers category-specific calibration if available and populated,
    otherwise falls back to the global calibration table.
    """
    category_name = (category or "default").strip() or "default"

    if category_calibration_tables:
        tables = category_calibration_tables.get("tables", {}) or {}
        category_table = tables.get(category_name)

        if category_table and int(category_table.get("count", 0)) > 0:
            return calibrate_probability(raw_probability, category_table)

    return calibrate_probability(raw_probability, global_calibration_table)


def calibration_report(
    backtest_summary: Dict[str, Any],
    *,
    num_bins: int = 10,
    min_bin_count: int = 3,
) -> Dict[str, Any]:
    """
    Convenience wrapper around backtesting output.

    Expected backtest_summary shape:
    {
      "records": [...],
      ...
    }
    """
    records = backtest_summary.get("records", []) or []

    global_table = build_calibration_table(
        records,
        num_bins=num_bins,
        min_bin_count=min_bin_count,
    )

    category_tables = build_category_calibration_tables(
        records,
        num_bins=num_bins,
        min_bin_count=min_bin_count,
    )

    return {
        "global": global_table,
        "global_diagnostics": calibration_diagnostics(global_table),
        "by_category": category_tables,
    }
