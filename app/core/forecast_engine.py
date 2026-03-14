import math
from typing import List, Dict, Any, Optional, Tuple

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
    """
    Conservative question-aware prior adjustment.
    Applies to all questions; a few topic-specific caps exist for obvious outlier cases.
    """
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
    """
    Converts scored claims into a conservative log-odds delta.
    Positive net_signal increases probability, negative net_signal decreases it.
    """
    diagnostics = claim_scoring.get("diagnostics", {}) or {}
    net_signal = float(claim_scoring.get("net_signal", 0.0))
    claim_count = int(diagnostics.get("claim_count_scored", 0))
    uncertainty_drag = float(diagnostics.get("uncertainty_drag", 0.0))

    if claim_count == 0:
        return 0.0, ["claim_signal: no_scored_claims_available"]

    # Conservative scaling to avoid extreme swings.
    base_delta = net_signal * 0.90

    # Mild trust boost when many claims exist, mild penalty when uncertainty is high.
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


def compute_probability(
    category: str,
    evidence: List[EvidenceItem],
    question_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns probability in 0..1.

    Pipeline:
    1) question-aware prior
    2) source research
    3) claim extraction
    4) claim scoring
    5) net claim signal -> log-odds update
    6) manual evidence -> log-odds update
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

    probability = _sigmoid(lo)

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
    summary = _build_summary(question_text or "", probability, claim_scoring_bundle)

    explanation = _build_explanation(
        question_text=question_text or "",
        base_rate_raw=base_rate_raw,
        base_rate_adjusted=base_rate_adjusted,
        probability=probability,
        confidence=confidence,
        question_signals=question_signals,
        claim_signals=claim_signals,
        contributions=contributions,
        research_bundle=research_bundle,
        extracted_claims_bundle=extracted_claims_bundle,
        claim_scoring_bundle=claim_scoring_bundle,
        reasoning=reasoning,
        summary=summary,
        pipeline_errors=pipeline_errors,
    )

    return {
        "probability": round(probability, 4),  # 0..1
        "confidence": round(confidence, 2),    # 0..100
        "base_rate": round(base_rate_adjusted, 4),
        "base_rate_raw": round(base_rate_raw, 4),
        "summary": summary,
        "question_signals": question_signals,
        "claim_signals": claim_signals,
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
        "diagnostics": claim_scoring_bundle.get("diagnostics", {}),
        "contributions": contributions,
        "pipeline_errors": pipeline_errors,
        "explanation_md": explanation,
    }


def _build_explanation(
    *,
    question_text: str,
    base_rate_raw: float,
    base_rate_adjusted: float,
    probability: float,
    confidence: float,
    question_signals: List[str],
    claim_signals: List[str],
    contributions: List[Dict[str, Any]],
    research_bundle: Dict[str, Any],
    extracted_claims_bundle: Dict[str, Any],
    claim_scoring_bundle: Dict[str, Any],
    reasoning: Dict[str, List[str]],
    summary: str,
    pipeline_errors: List[str],
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
    lines.append("- Methodik: **bayes_logodds_v1 + source_research_v1 + claim_extraction_v1 + claim_scoring_v1**")
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

    if claim_signals:
        lines.append("### Claim-Signale")
        for signal in claim_signals:
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
        f"uncertainty={claim_counts.get('uncertainty', 0)}, "
        f"background={claim_counts.get('background', 0)})"
    )
    lines.append(
        f"- Scored Claims: **{diagnostics.get('claim_count_scored', 0)}**, "
        f"net_signal=**{float(claim_scoring_bundle.get('net_signal', 0.0)):+.4f}**"
    )
    lines.append("")

    queries = research_bundle.get("queries", []) or []
    if queries:
        lines.append("### Suchanfragen")
        for query in queries[:8]:
            lines.append(f"- {query}")
        lines.append("")

    top_pro_claims = claim_scoring_bundle.get("top_pro_claims", []) or []
    top_contra_claims = claim_scoring_bundle.get("top_contra_claims", []) or []
    top_uncertainties = claim_scoring_bundle.get("top_uncertainties", []) or []

    if top_pro_claims:
        lines.append("### Top Pro Claims")
        for item in top_pro_claims[:5]:
            lines.append(
                f"- {item.get('claim_text', '')} "
                f"[w={float(item.get('final_weight', 0.0)):.2f}, "
                f"source={item.get('source_title', 'n/a')}]"
            )
        lines.append("")

    if top_contra_claims:
        lines.append("### Top Contra Claims")
        for item in top_contra_claims[:5]:
            lines.append(
                f"- {item.get('claim_text', '')} "
                f"[w={float(item.get('final_weight', 0.0)):.2f}, "
                f"source={item.get('source_title', 'n/a')}]"
            )
        lines.append("")

    if top_uncertainties:
        lines.append("### Top Uncertainty Claims")
        for item in top_uncertainties[:5]:
            lines.append(
                f"- {item.get('claim_text', '')} "
                f"[w={float(item.get('final_weight', 0.0)):.2f}, "
                f"source={item.get('source_title', 'n/a')}]"
            )
        lines.append("")

    sources = research_bundle.get("sources", []) or []
    if sources:
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
        lines.append("### Verwendete Quellen")
        lines.append("- Keine Onlinequellen verfügbar oder Recherche fehlgeschlagen.")

    lines.append("")
    lines.append("### Hinweis")
    lines.append("- Diese Version nutzt strukturierte Quellenrecherche, Claim-Extraktion, Claim-Scoring und ein konservatives Log-Odds-Update.")
    lines.append("- Nächste sinnvolle Ausbaustufen: Volltext-Extraktion, sauberere Claim-Normalisierung, Persistenz für Sources/Claims und echte Kalibrierung mit Brier-Score-Daten.")

    return "\n".join(lines)
