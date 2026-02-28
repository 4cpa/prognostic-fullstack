import math
from typing import List, Dict, Any
from app.models.evidence import EvidenceItem

BASE_RATES = {
    "politics": 0.30,
    "default": 0.25,
}

def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def compute_probability(category: str, evidence: List[EvidenceItem]) -> Dict[str, Any]:
    base = BASE_RATES.get(category, BASE_RATES["default"])
    lo = _logit(base)

    contributions = []
    for e in evidence:
        c = float(e.direction) * float(e.weight)
        contributions.append({
            "evidence_id": e.id,
            "indicator_type": e.indicator_type,
            "direction": e.direction,
            "weight": e.weight,
            "contribution": c,
        })
        lo += c

    p = _sigmoid(lo) * 100.0

    strength = sum(abs(c["contribution"]) for c in contributions)
    conf = min(95.0, 30.0 + strength * 20.0) if contributions else 35.0

    explanation = _build_explanation(base, p, conf, contributions)

    return {
        "probability": round(p, 2),
        "confidence": round(conf, 2),
        "base_rate": base,
        "contributions": contributions,
        "explanation_md": explanation,
    }

def _build_explanation(base: float, p: float, conf: float, contributions: List[dict]) -> str:
    lines = []
    lines.append("### Methodik: bayes_logodds_v1\n")
    lines.append(f"- Base-Rate (Kategorie): **{base*100:.1f}%**")
    lines.append(f"- Ergebnis (Posterior): **{p:.2f}%**")
    lines.append(f"- Confidence (MVP-Heuristik): **{conf:.2f}%**\n")

    if not contributions:
        lines.append("**Keine Evidenzen erfasst.** Prognose basiert aktuell nur auf Base-Rate.")
        return "\n".join(lines)

    lines.append("### Evidenz-Updates (additive Log-Odds)\n")
    for c in contributions:
        sign = "+" if c["contribution"] >= 0 else ""
        lines.append(
            f"- `{c['indicator_type']}` (id={c['evidence_id']}): "
            f"dir={c['direction']}, weight={c['weight']} → contribution={sign}{c['contribution']:.3f}"
        )

    lines.append("\n### Hinweis\n- Später: Kalibrierung (Brier Score), Source-Credibility, Time-Decay, Crowd-Module.")
    return "\n".join(lines)
