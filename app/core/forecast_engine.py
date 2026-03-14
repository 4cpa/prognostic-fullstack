import math
from typing import List, Dict, Any, Optional, Tuple

from sqlmodel import Session

from app.core.calibration import calibrate_probability
from app.core.calibration_service import (
    load_runtime_calibration,
    select_calibration_table_for_category,
)
from app.core.claim_extraction import extract_claims_from_sources
from app.core.claim_scoring import score_claims
from app.core.source_research import research_sources_for_question
from app.models.evidence import EvidenceItem


BASE_RATES = {
    "politics": 0.30,
    "economy": 0.40,
    "technology": 0.50,
    "security": 0.35,
    "default": 0.25,
}


def _clamp_probability(p: float) -> float:
    return min(max(p, 1e-6), 1 - 1e-6)


def _logit(p: float) -> float:
    p = _clamp_probability(p)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _normalize_text(text: Optional[str]) -> str:
    return (text or "").strip().lower()


def _infer_question_adjustment(category: str, question_text: Optional[str]) -> Tuple[float, List[str]]:
    base = BASE_RATES.get(category, BASE_RATES["default"])
    text = _normalize_text(question_text)
    signals: List[str] = []

    if not text:
        return base, signals

    adjusted = base

    if "weltkrieg" in text or "world war" in text:
        adjusted = min(adjusted, 0.05)
        signals.append("question_signal: world_war -> prior capped at 5.0%")

    if ("eu" in text or "europäische union" in text or "european union" in text) and (
        "zerbrechen" in text or "zerfall" in text or "breakup" in text or "collapse" in text
    ):
        adjusted = min(adjusted, 0.12)
        signals.append("question_signal: eu_breakup -> prior capped at 12.0%")

    if "ende 2026" in text or "31. dezember 2026" in text or "31 december 2026" in text:
        signals.append("question_signal: explicit_end_2026_horizon")

    return adjusted, signals


def _claims_to_logodds_delta(claim_scoring: Dict[str, Any]) -> Tuple[float, List[str]]:
    diagnostics = claim_scoring.get("diagnostics", {}) or {}
    net_signal = float(claim_scoring.get("net_signal", 0.0))
    claim_count = int(diagnostics.get("claim_count_scored", 0))
    uncertainty_drag = float(diagnostics.get("uncertainty_drag", 0.0))

    if claim_count == 0:
        return 0.0, ["claim_signal: no_scored_claims_available"]

    base_delta = net_signal * 0.90
    count_boost = min(0.25, max(0, claim_count - 3) * 0.02)
    uncertainty_penalty = min(0.30, uncertainty_drag * 0.50)

    delta = base_delta + count_boost - uncertainty_penalty
    delta = max(-1.50, min(1.50, delta))

    signals = [
        (
            "claim_signal: "
            f"net_signal={net_signal:+.4f}, "
            f"claim_count={claim_count}, "
            f"count_boost={count_boost:+.4f}, "
            f"uncertainty_penalty={uncertainty_penalty:+.4f}, "
            f"logodds_delta={delta:+.4f}"
        )
    ]

    return delta, signals


def _manual_evidence_to_logodds(evidence: List[EvidenceItem]) -> Tuple[float, List[Dict[str, Any]]]:
    delta = 0.0
    contributions: List[Dict[str, Any]] = []

    for e in evidence:
        contribution = float(e.direction) * float(e.weight)
        delta += contribution
        contributions.append(
            {
                "evidence_id": e.id,
                "indicator_type": e.indicator_type,
                "direction": float(e.direction),
                "weight": float(e.weight),
                "contribution": round(contribution, 4),
            }
        )

    return delta, contributions


def _build_reasoning_from_scored_claims(claim_scoring: Dict[str, Any]) -> Dict[str, List[str]]:
    def _fmt(items: List[Dict[str, Any]]) -> List[str]:
        bullets: List[str] = []
        for item in items[:5]:
            text = str(item.get("claim_text", "")).strip()
            title = str(item.get("source_title", "")).strip()
            source_type = str(item.get("source_type", "")).strip()
            weight = float(item.get("final_weight", 0.0))
            if not text:
                continue
            suffix = []
            if title:
                suffix.append(title)
            if source_type:
                suffix.append(source_type)
            suffix.append(f"w={weight:.2f}")
            bullets.append(f"{text} ({', '.join(suffix)})")
        return bullets

    return {
        "pro": _fmt(claim_scoring.get("top_pro_claims", []) or []),
        "contra": _fmt(claim_scoring.get("top_contra_claims", []) or []),
        "uncertainties": _fmt(claim_scoring.get("top_uncertainties", []) or []),
        "background": _fmt(claim_scoring.get("top_background", []) or []),
    }


def _build_summary(question_text: str, probability: float, claim_scoring: Dict[str, Any]) -> str:
    pct = probability * 100.0
    top_pro = claim_scoring.get("top_pro_claims", []) or []
    top_contra = claim_scoring.get("top_contra_claims", []) or []

    if pct < 10:
        qualifier = "derzeit eher unwahrscheinlich"
    elif pct < 25:
        qualifier = "derzeit eher nicht wahrscheinlich"
    elif pct < 40:
        qualifier = "derzeit möglich, aber unter 50%"
    elif pct < 60:
        qualifier = "derzeit ungefähr ausgeglichen"
    elif pct < 75:
        qualifier = "derzeit eher wahrscheinlich"
    else:
        qualifier = "derzeit klar wahrscheinlich"

    if top_contra:
        anchor = str(top_contra[0].get("claim_text", "")).strip()
        return (
            f"Für die Frage „{question_text}“ erscheint das Ereignis mit {pct:.1f}% {qualifier}. "
            f"Das stärkste Gegensignal ist derzeit: {anchor}"
        )

    if top_pro:
        anchor = str(top_pro[0].get("claim_text", "")).strip()
        return (
            f"Für die Frage „{question_text}“ erscheint das Ereignis mit {pct:.1f}% {qualifier}. "
            f"Das stärkste unterstützende Signal ist derzeit: {anchor}"
        )

    return (
        f"Für die Frage „{question_text}“ erscheint das Ereignis mit {pct:.1f}% {qualifier}. "
        "Die aktuelle Quellenlage liefert noch keine stark gewichteten strukturierten Claims."
    )


def _default_calibration_table() -> Dict[str, Any]:
    bins = []
    step = 0.1
    lower = 0.0
    for i in range(10):
        upper = 1.0 if i == 9 else round(lower + step, 6)
        bins.append(
            {
                "bucket": f"{int(lower * 100):02d}-{int(upper * 100):02d}%",
                "lower": round(lower, 6),
                "upper": round(upper, 6),
                "count": 0,
                "avg_predicted": round((lower + upper) / 2.0, 6),
                "avg_observed": round((lower + upper) / 2.0, 6),
                "correction": 0.0,
            }
        )
        lower = upper

    return {
        "num_bins": 10,
        "min_bin_count": 3,
        "count": 0,
        "avg_abs_gap": 0.0,
        "bins": bins,
    }


def _load_calibration_table(
    category: str, session: Optional[Session]
) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    signals: List[str] = []

    if session is None:
        signals.append("calibration_signal: no_session_available -> using neutral calibration")
        table = _default_calibration_table()
        runtime = {"global": table, "by_category": {"count_categories": 0, "tables": {}}, "meta": {}}
        return table, runtime, signals

    try:
        runtime = load_runtime_calibration(session)
        table = select_calibration_table_for_category(runtime, category)

        if not table:
            signals.append("calibration_signal: empty_runtime_table -> using neutral calibration")
            table = _default_calibration_table()

        meta = runtime.get("meta", {}) or {}
        signals.append(
            "calibration_signal: "
            f"record_count={int(meta.get('record_count', 0) or 0)}, "
            f"category={category}, "
            f"table_count={int(table.get('count', 0) or 0)}, "
            f"avg_abs_gap={float(table.get('avg_abs_gap', 0.0) or 0.0):.4f}"
        )
        return table, runtime, signals

    except Exception as exc:
        signals.append(f"calibration_signal: runtime_load_failed -> {str(exc)}")
        table = _default_calibration_table()
        runtime = {"global": table, "by_category": {"count_categories": 0, "tables": {}}, "meta": {}}
        return table, runtime, signals


def compute_probability(
    category: str,
    evidence: List[EvidenceItem],
    question_text: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    base_rate_raw = BASE_RATES.get(category, BASE_RATES["default"])
    base_rate_adjusted, question_signals = _infer_question_adjustment(category, question_text)

    research_bundle: Dict[str, Any] = {
        "question_text": question_text or "",
        "queries": [],
        "sources": [],
        "source_counts": {},
        "reasoning": {"pro": [], "contra": [], "uncertainties": []},
    }
    extracted_claims_bundle: Dict[str, Any] = {
        "question_text": question_text or "",
        "claims": [],
        "claim_counts": {"pro": 0, "contra": 0, "uncertainty": 0, "background": 0},
    }
    claim_scoring_bundle: Dict[str, Any] = {
        "scored_claims": [],
        "top_pro_claims": [],
        "top_contra_claims": [],
        "top_uncertainties": [],
        "top_background": [],
        "net_signal": 0.0,
        "diagnostics": {},
    }
    pipeline_errors: List[str] = []

    if question_text:
        try:
            research_bundle = research_sources_for_question(question_text)
        except Exception as exc:
            pipeline_errors.append(f"research_error: {str(exc)}")

        try:
            extracted_claims_bundle = extract_claims_from_sources(
                question_text=question_text,
                sources=research_bundle.get("sources", []) or [],
            )
        except Exception as exc:
            pipeline_errors.append(f"claim_extraction_error: {str(exc)}")

        try:
            claim_scoring_bundle = score_claims(
                extracted_claims_bundle.get("claims", []) or []
            )
        except Exception as exc:
            pipeline_errors.append(f"claim_scoring_error: {str(exc)}")

    lo = _logit(base_rate_adjusted)

    claim_delta, claim_signals = _claims_to_logodds_delta(claim_scoring_bundle)
    lo += claim_delta

    manual_delta, contributions = _manual_evidence_to_logodds(evidence)
    lo += manual_delta

    raw_probability = _sigmoid(lo)

    calibration_table, runtime_calibration, calibration_signals = _load_calibration_table(category, session)
    calibrated_probability = calibrate_probability(raw_probability, calibration_table)

    source_count = len(research_bundle.get("sources", []) or [])
    claim_count = len(claim_scoring_bundle.get("scored_claims", []) or [])
    official_count = int((research_bundle.get("source_counts", {}) or {}).get("official", 0))
    wire_count = int((research_bundle.get("source_counts", {}) or {}).get("wire", 0))
    evidence_strength = sum(abs(float(c.get("contribution", 0.0))) for c in contributions)
    uncertainty_drag = float((claim_scoring_bundle.get("diagnostics", {}) or {}).get("uncertainty_drag", 0.0))

    confidence = 20.0
    confidence += min(20.0, source_count * 1.1)
    confidence += min(18.0, claim_count * 0.9)
    confidence += min(10.0, official_count * 2.0)
    confidence += min(8.0, wire_count * 1.5)
    confidence += min(18.0, evidence_strength * 14.0)
    confidence -= min(15.0, uncertainty_drag * 20.0)
    confidence = min(95.0, max(5.0, confidence))

    reasoning = _build_reasoning_from_scored_claims(claim_scoring_bundle)
    summary = _build_summary(question_text or "", calibrated_probability, claim_scoring_bundle)

    explanation = _build_explanation(
        question_text=question_text or "",
        base_rate_raw=base_rate_raw,
        base_rate_adjusted=base_rate_adjusted,
        raw_probability=raw_probability,
        calibrated_probability=calibrated_probability,
        confidence=confidence,
        question_signals=question_signals,
        claim_signals=claim_signals,
        calibration_signals=calibration_signals,
        contributions=contributions,
        research_bundle=research_bundle,
        extracted_claims_bundle=extracted_claims_bundle,
        claim_scoring_bundle=claim_scoring_bundle,
        calibration_table=calibration_table,
        runtime_calibration=runtime_calibration,
        reasoning=reasoning,
        summary=summary,
        pipeline_errors=pipeline_errors,
    )

    return {
        "probability": round(calibrated_probability, 4),
        "raw_probability": round(raw_probability, 4),
        "calibrated_probability": round(calibrated_probability, 4),
        "confidence": round(confidence, 2),
        "base_rate": round(base_rate_adjusted, 4),
        "base_rate_raw": round(base_rate_raw, 4),
        "summary": summary,
        "question_signals": question_signals,
        "claim_signals": claim_signals,
        "calibration_signals": calibration_signals,
        "reasoning": reasoning,
        "source_queries": research_bundle.get("queries", []),
        "sources": research_bundle.get("sources", []),
        "source_counts": research_bundle.get("source_counts", {}),
        "claims": extracted_claims_bundle.get("claims", []),
        "claim_counts": extracted_claims_bundle.get("claim_counts", {}),
        "scored_claims": claim_scoring_bundle.get("scored_claims", []),
        "top_pro_claims": claim_scoring_bundle.get("top_pro_claims", []),
        "top_contra_claims": claim_scoring_bundle.get("top_contra_claims", []),
        "top_uncertainties": claim_scoring_bundle.get("top_uncertainties", []),
        "top_background": claim_scoring_bundle.get("top_background", []),
        "net_signal": round(float(claim_scoring_bundle.get("net_signal", 0.0)), 4),
        "diagnostics": {
            **(claim_scoring_bundle.get("diagnostics", {}) or {}),
            "raw_probability": round(raw_probability, 6),
            "calibrated_probability": round(calibrated_probability, 6),
            "calibration_count": int(calibration_table.get("count", 0) or 0),
            "calibration_avg_abs_gap": float(calibration_table.get("avg_abs_gap", 0.0) or 0.0),
            "calibration_record_count": int((runtime_calibration.get("meta", {}) or {}).get("record_count", 0) or 0),
            "overall_brier_score": float((runtime_calibration.get("meta", {}) or {}).get("overall_brier_score", 0.0) or 0.0),
            "overall_mae": float((runtime_calibration.get("meta", {}) or {}).get("overall_mae", 0.0) or 0.0),
            "overall_rmse": float((runtime_calibration.get("meta", {}) or {}).get("overall_rmse", 0.0) or 0.0),
        },
        "calibration": calibration_table,
        "runtime_calibration_meta": runtime_calibration.get("meta", {}) or {},
        "contributions": contributions,
        "pipeline_errors": pipeline_errors,
        "explanation_md": explanation,
    }


def _build_explanation(
    *,
    question_text: str,
    base_rate_raw: float,
    base_rate_adjusted: float,
    raw_probability: float,
    calibrated_probability: float,
    confidence: float,
    question_signals: List[str],
    claim_signals: List[str],
    calibration_signals: List[str],
    contributions: List[Dict[str, Any]],
    research_bundle: Dict[str, Any],
    extracted_claims_bundle: Dict[str, Any],
    claim_scoring_bundle: Dict[str, Any],
    calibration_table: Dict[str, Any],
    runtime_calibration: Dict[str, Any],
    reasoning: Dict[str, List[str]],
    summary: str,
    pipeline_errors: List[str],
) -> str:
    lines: List[str] = []

    lines.append("### Prognose")
    lines.append(f"- Frage: **{question_text or 'n/a'}**")
    lines.append(f"- Rohwahrscheinlichkeit: **{raw_probability * 100:.2f}%**")
    lines.append(f"- Kalibrierte Eintrittswahrscheinlichkeit: **{calibrated_probability * 100:.2f}%**")
    lines.append(f"- Confidence: **{confidence:.2f}%**")
    lines.append("")

    lines.append("### Kurzbegründung")
    lines.append(summary)
    lines.append("")

    lines.append("### Methodik")
    lines.append("- Methodik: **bayes_logodds_v1 + source_research_v1 + claim_extraction_v1 + claim_scoring_v1 + calibration_v1**")
    lines.append(f"- Base-Rate (Kategorie, roh): **{base_rate_raw * 100:.1f}%**")
    if abs(base_rate_adjusted - base_rate_raw) > 1e-9:
        lines.append(f"- Base-Rate (nach Frage-Signalen): **{base_rate_adjusted * 100:.1f}%**")
    lines.append(f"- Rohwahrscheinlichkeit (vor Kalibrierung): **{raw_probability * 100:.2f}%**")
    lines.append(f"- Ergebnis (kalibriert): **{calibrated_probability * 100:.2f}%**")
    lines.append(f"- Confidence (Heuristik): **{confidence:.2f}%**")
    lines.append("")

    if question_signals:
        lines.append("### Frage-Signale")
        for signal in question_signals:
            lines.append(f"- {signal}")
        lines.append("")

    if claim_signals:
        lines.append("### Claim-Signale")
        for signal in claim_signals:
            lines.append(f"- {signal}")
        lines.append("")

    if calibration_signals:
        lines.append("### Kalibrierungs-Signale")
        for signal in calibration_signals:
            lines.append(f"- {signal}")
        lines.append("")

    if pipeline_errors:
        lines.append("### Pipeline-Hinweise")
        for err in pipeline_errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("### Gründe, die für das Eintreten sprechen")
    for point in reasoning.get("pro", [])[:5]:
        lines.append(f"- {point}")
    if not reasoning.get("pro"):
        lines.append("- Keine stark gewichteten Pro-Claims extrahiert.")
    lines.append("")

    lines.append("### Gründe, die gegen das Eintreten sprechen")
    for point in reasoning.get("contra", [])[:5]:
        lines.append(f"- {point}")
    if not reasoning.get("contra"):
        lines.append("- Keine stark gewichteten Contra-Claims extrahiert.")
    lines.append("")

    lines.append("### Unsicherheiten")
    for point in reasoning.get("uncertainties", [])[:5]:
        lines.append(f"- {point}")
    if not reasoning.get("uncertainties"):
        lines.append("- Keine stark gewichteten Unsicherheits-Claims extrahiert.")
    lines.append("")

    if contributions:
        lines.append("### Manuelle Evidenz-Updates (additive Log-Odds)")
        for c in contributions:
            sign = "+" if float(c.get("contribution", 0.0)) >= 0 else ""
            lines.append(
                f"- `{c['indicator_type']}` (id={c['evidence_id']}): "
                f"dir={c['direction']}, weight={c['weight']} → contribution={sign}{float(c['contribution']):.4f}"
            )
        lines.append("")

    source_counts = research_bundle.get("source_counts", {}) or {}
    claim_counts = extracted_claims_bundle.get("claim_counts", {}) or {}
    diagnostics = claim_scoring_bundle.get("diagnostics", {}) or {}

    lines.append("### Strukturierte Pipeline-Statistik")
    lines.append(
        f"- Quellen: **{len(research_bundle.get('sources', []) or [])}** "
        f"(official={source_counts.get('official', 0)}, "
        f"wire={source_counts.get('wire', 0)}, "
        f"research={source_counts.get('research', 0)}, "
        f"major_media={source_counts.get('major_media', 0)}, "
        f"other={source_counts.get('other', 0)})"
    )
    lines.append(
        f"- Claims: **{len(extracted_claims_bundle.get('claims', []) or [])}** "
        f"(pro={claim_counts.get('pro', 0)}, "
        f"contra={claim_counts.get('contra', 0)}, "
        f"
