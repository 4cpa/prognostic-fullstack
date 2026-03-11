import math
from typing import List, Dict, Any, Optional, Tuple

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
    """
    Returns:
        adjusted_base_rate in 0..1
        list of human-readable signals used for the adjustment

    This is intentionally simple MVP logic so obviously different questions
    do not collapse to the exact same default number when no evidence exists.
    """
    base = BASE_RATES.get(category, BASE_RATES["default"])
    text = _normalize_text(question_text)
    signals: List[str] = []

    if not text:
        return base, signals

    adjusted = base

    if "weltkrieg" in text or "world war" in text:
        adjusted = min(adjusted, 0.05)
        signals.append("question_signal: world_war -> base capped at 5.0%")

    if ("eu" in text or "europäische union" in text or "european union" in text) and (
        "zerbrechen" in text or "zerfall" in text or "breakup" in text or "collapse" in text
    ):
        adjusted = min(adjusted, 0.12)
        signals.append("question_signal: eu_breakup -> base capped at 12.0%")

    if "ende 2026" in text or "31. dezember 2026" in text or "31 december 2026" in text:
        signals.append("question_signal: explicit_end_2026_horizon")

    return adjusted, signals


def compute_probability(
    category: str,
    evidence: List[EvidenceItem],
    question_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns probability in 0..1.

    Human-readable explanations render percentages, but the stored / API value
    stays normalized to avoid double percentage conversion bugs.
    """
    base_rate_raw = BASE_RATES.get(category, BASE_RATES["default"])
    base_rate_adjusted, question_signals = _infer_question_adjustment(category, question_text)

    lo = _logit(base_rate_adjusted)

    contributions = []
    for e in evidence:
        contribution = float(e.direction) * float(e.weight)
        contributions.append(
            {
                "evidence_id": e.id,
                "indicator_type": e.indicator_type,
                "direction": float(e.direction),
                "weight": float(e.weight),
                "contribution": contribution,
            }
        )
        lo += contribution

    probability = _sigmoid(lo)  # 0..1, never 0..100 here

    strength = sum(abs(c["contribution"]) for c in contributions)
    confidence = min(95.0, 30.0 + strength * 20.0) if contributions else 35.0

    explanation = _build_explanation(
        base_rate_raw=base_rate_raw,
        base_rate_adjusted=base_rate_adjusted,
        probability=probability,
        confidence=confidence,
        contributions=contributions,
        question_signals=question_signals,
    )

    return {
        "probability": round(probability, 4),  # 0..1
        "confidence": round(confidence, 2),    # 0..100
        "base_rate": round(base_rate_adjusted, 4),  # 0..1
        "base_rate_raw": round(base_rate_raw, 4),   # 0..1
        "question_signals": question_signals,
        "contributions": contributions,
        "explanation_md": explanation,
    }


def _build_explanation(
    base_rate_raw: float,
    base_rate_adjusted: float,
    probability: float,
    confidence: float,
    contributions: List[Dict[str, Any]],
    question_signals: List[str],
) -> str:
    lines: List[str] = []

    lines.append("### Methodik: bayes_logodds_v1")
    lines.append(f"- Base-Rate (Kategorie, roh): **{base_rate_raw * 100:.1f}%**")

    if abs(base_rate_adjusted - base_rate_raw) > 1e-9:
        lines.append(
            f"- Base-Rate (nach Frage-Signalen): **{base_rate_adjusted * 100:.1f}%**"
        )

    lines.append(f"- Ergebnis (Posterior): **{probability * 100:.2f}%**")
    lines.append(f"- Confidence (MVP-Heuristik): **{confidence:.2f}%**")

    if question_signals:
        lines.append("")
        lines.append("### Frage-Signale")
        for signal in question_signals:
            lines.append(f"- {signal}")

    if not contributions:
        lines.append("")
        lines.append("**Keine Evidenzen erfasst.** Prognose basiert aktuell auf Base-Rate plus einfachen Frage-Signalen.")
        lines.append("")
        lines.append("### Hinweis")
        lines.append("- Später: Kalibrierung (Brier Score), Source-Credibility, Time-Decay, Crowd-Module.")
        return "\n".join(lines)

    lines.append("")
    lines.append("### Evidenz-Updates (additive Log-Odds)")
    for c in contributions:
        sign = "+" if c["contribution"] >= 0 else ""
        lines.append(
            f"- `{c['indicator_type']}` (id={c['evidence_id']}): "
            f"dir={c['direction']}, weight={c['weight']} "
            f"→ contribution={sign}{c['contribution']:.3f}"
        )

    lines.append("")
    lines.append("### Hinweis")
    lines.append("- Später: Kalibrierung (Brier Score), Source-Credibility, Time-Decay, Crowd-Module.")

    return "\n".join(lines)
