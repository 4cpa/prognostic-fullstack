import math
from typing import List, Dict, Any, Optional, Tuple

from app.core.source_research import build_summary, research_sources_for_question
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
        signals.append("question_signal: world_war -> base capped at 5.0%")

    if ("eu" in text or "europäische union" in text or "european union" in text) and (
        "zerbrechen" in text or "zerfall" in text or "breakup" in text or "collapse" in text
    ):
        adjusted = min(adjusted, 0.12)
        signals.append("question_signal: eu_breakup -> base capped at 12.0%")

    if "ende 2026" in text or "31. dezember 2026" in text or "31 december 2026" in text:
        signals.append("question_signal: explicit_end_2026_horizon")

    return adjusted, signals


def _research_signal_delta(question_text: Optional[str], research_bundle: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Converts source balance into a small additive log-odds adjustment.
    Conservative by design: sources should influence, not dominate.
    """
    if not question_text:
        return 0.0, []

    sources = research_bundle.get("sources", []) or []
    if not sources:
        return 0.0, ["research_signal: no_sources_available"]

    pro_weight = 0.0
    contra_weight = 0.0
    uncertainty_weight = 0.0
    signals: List[str] = []

    for source in sources:
        overall = float(source.get("overall_score", 0.0))
        signal_strength = float(source.get("signal_strength", 0.0))
        weight = overall * max(signal_strength, 0.10)
        stance = source.get("stance", "neutral")

        if stance == "pro":
            pro_weight += weight
        elif stance == "contra":
            contra_weight += weight
        else:
            uncertainty_weight += weight

    net = pro_weight - contra_weight

    # konservative Kappung, damit Research die Base Rate nicht sprengt
    delta = max(-1.25, min(1.25, net * 0.60))

    signals.append(
        f"research_signal: pro_weight={pro_weight:.3f}, contra_weight={contra_weight:.3f}, "
        f"uncertainty_weight={uncertainty_weight:.3f}, delta={delta:+.3f}"
    )

    return delta, signals


def compute_probability(
    category: str,
    evidence: List[EvidenceItem],
    question_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns probability in 0..1.

    Adds a first systematic source-research layer:
    - query expansion
    - public source retrieval
    - source classification
    - source-weighted reasoning
    """
    base_rate_raw = BASE_RATES.get(category, BASE_RATES["default"])
    base_rate_adjusted, question_signals = _infer_question_adjustment(category, question_text)

    research_bundle: Dict[str, Any] = {
        "question_text": question_text or "",
        "queries": [],
        "sources": [],
        "source_counts": {},
        "reasoning": {"pro": [], "contra": [], "uncertainties": []},
    }

    if question_text:
        try:
            research_bundle = research_sources_for_question(question_text)
        except Exception as exc:
            research_bundle = {
                "question_text": question_text,
                "queries": [],
                "sources": [],
                "source_counts": {},
                "reasoning": {
                    "pro": [],
                    "contra": [],
                    "uncertainties": [f"research_error: {str(exc)}"],
                },
            }

    lo = _logit(base_rate_adjusted)

    research_delta, research_signals = _research_signal_delta(question_text, research_bundle)
    lo += research_delta

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

    probability = _sigmoid(lo)

    evidence_strength = sum(abs(c["contribution"]) for c in contributions)
    source_count = len(research_bundle.get("sources", []) or [])
    official_count = int((research_bundle.get("source_counts", {}) or {}).get("official", 0))
    wire_count = int((research_bundle.get("source_counts", {}) or {}).get("wire", 0))

    confidence = 25.0
    confidence += min(25.0, evidence_strength * 18.0)
    confidence += min(20.0, source_count * 1.2)
    confidence += min(10.0, official_count * 2.5)
    confidence += min(8.0, wire_count * 2.0)
    confidence = min(95.0, confidence)

    reasoning = research_bundle.get("reasoning", {}) or {}
    summary = build_summary(question_text or "", probability, reasoning)

    explanation = _build_explanation(
        question_text=question_text or "",
        base_rate_raw=base_rate_raw,
        base_rate_adjusted=base_rate_adjusted,
        probability=probability,
        confidence=confidence,
        contributions=contributions,
        question_signals=question_signals,
        research_signals=research_signals,
        research_bundle=research_bundle,
        summary=summary,
    )

    return {
        "probability": round(probability, 4),  # 0..1
        "confidence": round(confidence, 2),    # 0..100
        "base_rate": round(base_rate_adjusted, 4),      # 0..1
        "base_rate_raw": round(base_rate_raw, 4),       # 0..1
        "summary": summary,
        "question_signals": question_signals,
        "research_signals": research_signals,
        "reasoning": reasoning,
        "source_queries": research_bundle.get("queries", []),
        "sources": research_bundle.get("sources", []),
        "source_counts": research_bundle.get("source_counts", {}),
        "contributions": contributions,
        "explanation_md": explanation,
    }


def _build_explanation(
    *,
    question_text: str,
    base_rate_raw: float,
    base_rate_adjusted: float,
    probability: float,
    confidence: float,
    contributions: List[Dict[str, Any]],
    question_signals: List[str],
    research_signals: List[str],
    research_bundle: Dict[str, Any],
    summary: str,
) -> str:
    lines: List[str] = []

    lines.append("### Prognose")
    lines.append(f"- Frage: **{question_text or 'n/a'}**")
    lines.append(f"- Geschätzte Eintrittswahrscheinlichkeit: **{probability * 100:.2f}%**")
    lines.append(f"- Confidence: **{confidence:.2f}%**")
    lines.append("")

    lines.append("### Kurzbegründung")
    lines.append(summary)
    lines.append("")

    lines.append("### Methodik")
    lines.append("- Methodik: **bayes_logodds_v1 + source_research_v1**")
    lines.append(f"- Base-Rate (Kategorie, roh): **{base_rate_raw * 100:.1f}%**")
    if abs(base_rate_adjusted - base_rate_raw) > 1e-9:
        lines.append(f"- Base-Rate (nach Frage-Signalen): **{base_rate_adjusted * 100:.1f}%**")
    lines.append(f"- Ergebnis (Posterior): **{probability * 100:.2f}%**")
    lines.append(f"- Confidence (Heuristik): **{confidence:.2f}%**")
    lines.append("")

    if question_signals:
        lines.append("### Frage-Signale")
        for signal in question_signals:
            lines.append(f"- {signal}")
        lines.append("")

    if research_signals:
        lines.append("### Research-Signale")
        for signal in research_signals:
            lines.append(f"- {signal}")
        lines.append("")

    reasoning = research_bundle.get("reasoning", {}) or {}
    pro_points = reasoning.get("pro", []) or []
    contra_points = reasoning.get("contra", []) or []
    uncertainty_points = reasoning.get("uncertainties", []) or []

    lines.append("### Gründe, die für das Eintreten sprechen")
    for point in pro_points[:5]:
        lines.append(f"- {point}")
    if not pro_points:
        lines.append("- Keine starken Pro-Signale aus der aktuellen Quellenlage extrahiert.")
    lines.append("")

    lines.append("### Gründe, die gegen das Eintreten sprechen")
    for point in contra_points[:5]:
        lines.append(f"- {point}")
    if not contra_points:
        lines.append("- Keine starken Contra-Signale aus der aktuellen Quellenlage extrahiert.")
    lines.append("")

    lines.append("### Unsicherheiten")
    for point in uncertainty_points[:5]:
        lines.append(f"- {point}")
    if not uncertainty_points:
        lines.append("- Keine spezifischen Unsicherheiten extrahiert; Modellrisiko bleibt bestehen.")
    lines.append("")

    if contributions:
        lines.append("### Manuelle Evidenz-Updates (additive Log-Odds)")
        for c in contributions:
            sign = "+" if c["contribution"] >= 0 else ""
            lines.append(
                f"- `{c['indicator_type']}` (id={c['evidence_id']}): "
                f"dir={c['direction']}, weight={c['weight']} → contribution={sign}{c['contribution']:.3f}"
            )
        lines.append("")

    source_counts = research_bundle.get("source_counts", {}) or {}
    lines.append("### Quellenbasis")
    lines.append(
        f"- Quellenanzahl: **{len(research_bundle.get('sources', []) or [])}** "
        f"(official={source_counts.get('official', 0)}, "
        f"wire={source_counts.get('wire', 0)}, "
        f"research={source_counts.get('research', 0)}, "
        f"major_media={source_counts.get('major_media', 0)}, "
        f"other={source_counts.get('other', 0)})"
    )

    queries = research_bundle.get("queries", []) or []
    if queries:
        lines.append("- Suchanfragen:")
        for query in queries[:8]:
            lines.append(f"  - {query}")

    sources = research_bundle.get("sources", []) or []
    if sources:
        lines.append("")
        lines.append("### Verwendete Quellen (Top-Auswahl)")
        for source in sources[:12]:
            title = source.get("title", "untitled")
            publisher = source.get("publisher", source.get("domain", "unknown"))
            source_type = source.get("source_type", "other")
            overall_score = float(source.get("overall_score", 0.0))
            stance = source.get("stance", "neutral")
            url = source.get("url", "")
            published_at = source.get("published_at") or "n/a"

            lines.append(
                f"- **{publisher}** [{source_type}, stance={stance}, score={overall_score:.2f}, published={published_at}]"
            )
            lines.append(f"  - {title}")
            if url:
                lines.append(f"  - {url}")
    else:
        lines.append("- Keine Onlinequellen verfügbar oder Recherche fehlgeschlagen.")

    lines.append("")
    lines.append("### Hinweis")
    lines.append("- Diese erste Version nutzt systematische Query-Expansion, öffentliche Suchquellen, Quellendiversität und heuristische Gewichtung.")
    lines.append("- Als nächste Ausbaustufen sinnvoll: HTML-Volltext-Extraktion, Claim-Extraction, Dedupe über Textähnlichkeit, Kalibrierung mit Brier Score und besseres Time-Decay.")

    return "\n".join(lines)
