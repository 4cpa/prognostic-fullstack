from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
import math
import re


# Optional project imports.
# The file is written so that it still behaves defensively if one of these modules
# is temporarily missing or has a different interface in the current repo state.
try:
    from app.core.source_research import research_sources as _research_sources  # type: ignore
except Exception:  # pragma: no cover
    _research_sources = None

try:
    from app.core.claim_extraction import extract_claims as _extract_claims  # type: ignore
except Exception:  # pragma: no cover
    _extract_claims = None

try:
    from app.core.claim_scoring import score_claims as _score_claims  # type: ignore
except Exception:  # pragma: no cover
    _score_claims = None

try:
    from app.core.calibration_service import (
        get_runtime_calibration as _get_runtime_calibration,  # type: ignore
        apply_runtime_calibration as _apply_runtime_calibration,  # type: ignore
    )
except Exception:  # pragma: no cover
    _get_runtime_calibration = None
    _apply_runtime_calibration = None


@dataclass
class EngineConfig:
    max_sources: int = 8
    max_claims: int = 20
    top_claims_per_bucket: int = 3
    prior_probability: float = 0.50
    min_confidence: float = 0.05
    max_confidence: float = 0.95


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalize_probability_value(probability: Optional[float]) -> Optional[float]:
    if probability is None:
        return None

    value = _safe_float(probability)
    if value is None:
        return None

    if value < 0:
        value = 0.0

    # Defensive support for older 0..100 flows.
    if value > 1.0:
        value = value / 100.0

    return _clamp(value, 0.0, 1.0)


def _normalize_score(value: Any, default: float = 0.0) -> float:
    parsed = _safe_float(value, default)
    if parsed is None:
        return default

    # Defensive support for score values that may still appear in 0..100 form.
    if parsed > 1.0:
        parsed = parsed / 100.0

    return _clamp(parsed, 0.0, 1.0)


def _clean_text(text: Any, fallback: str = "") -> str:
    if text is None:
        return fallback
    cleaned = " ".join(str(text).strip().split())
    return cleaned or fallback


def _question_text(question: Any) -> str:
    if isinstance(question, str):
        return _clean_text(question, "this question")

    if question is None:
        return "this question"

    for attr in ("title", "question", "text", "prompt"):
        value = getattr(question, attr, None)
        if value:
            return _clean_text(value, "this question")

    return "this question"


def _question_category(question: Any) -> Optional[str]:
    if question is None:
        return None
    for attr in ("category", "topic", "domain"):
        value = getattr(question, attr, None)
        if value:
            return _clean_text(value)
    return None


def _source_to_dict(source: Any) -> dict[str, Any]:
    if isinstance(source, dict):
        item = dict(source)
    else:
        item = {
            "title": getattr(source, "title", None),
            "url": getattr(source, "url", None),
            "domain": getattr(source, "domain", None),
            "published_at": getattr(source, "published_at", None),
            "excerpt": getattr(source, "excerpt", None),
            "summary": getattr(source, "summary", None),
            "relevance_score": getattr(source, "relevance_score", None),
            "weight": getattr(source, "weight", None),
            "source_type": getattr(source, "source_type", None),
        }

    item["title"] = _clean_text(item.get("title"))
    item["url"] = item.get("url")
    item["domain"] = _clean_text(item.get("domain"))
    item["published_at"] = item.get("published_at")
    item["excerpt"] = _clean_text(item.get("excerpt"))
    item["summary"] = _clean_text(item.get("summary"))
    item["relevance_score"] = _normalize_score(item.get("relevance_score"), 0.0)
    item["weight"] = _normalize_score(item.get("weight"), item["relevance_score"])
    if "source_type" in item:
        item["source_type"] = _clean_text(item.get("source_type"))
    return item


def _claim_direction_from_text(value: Any) -> str:
    text = _clean_text(value).lower()
    if text in {"pro", "support", "supports", "positive", "yes", "for"}:
        return "pro"
    if text in {"contra", "against", "negative", "no", "con"}:
        return "contra"
    return "uncertain"


def _claim_to_dict(claim: Any) -> dict[str, Any]:
    if isinstance(claim, dict):
        item = dict(claim)
    else:
        item = {
            "claim_text": getattr(claim, "claim_text", None) or getattr(claim, "text", None),
            "claim_type": getattr(claim, "claim_type", None) or getattr(claim, "type", None),
            "source_url": getattr(claim, "source_url", None),
            "source_title": getattr(claim, "source_title", None),
            "source_type": getattr(claim, "source_type", None),
            "claim_confidence": getattr(claim, "claim_confidence", None)
            or getattr(claim, "confidence", None),
            "time_relevance": getattr(claim, "time_relevance", None),
            "source_quality_weight": getattr(claim, "source_quality_weight", None),
            "relevance_weight": getattr(claim, "relevance_weight", None)
            or getattr(claim, "relevance_score", None),
            "freshness_weight": getattr(claim, "freshness_weight", None),
            "final_weight": getattr(claim, "final_weight", None) or getattr(claim, "weight", None),
            "direction": getattr(claim, "direction", None) or getattr(claim, "stance", None),
            "signed_weight": getattr(claim, "signed_weight", None),
            "explanation": getattr(claim, "explanation", None),
        }

    item["claim_text"] = _clean_text(item.get("claim_text"), "Unnamed claim")
    item["claim_type"] = _clean_text(item.get("claim_type"))
    item["source_url"] = item.get("source_url")
    item["source_title"] = _clean_text(item.get("source_title"))
    item["source_type"] = _clean_text(item.get("source_type"))
    item["claim_confidence"] = _normalize_score(item.get("claim_confidence"), 0.5)
    item["time_relevance"] = _normalize_score(item.get("time_relevance"), 0.5)
    item["source_quality_weight"] = _normalize_score(item.get("source_quality_weight"), 0.5)
    item["relevance_weight"] = _normalize_score(item.get("relevance_weight"), 0.5)
    item["freshness_weight"] = _normalize_score(item.get("freshness_weight"), 0.5)
    item["final_weight"] = _normalize_score(
        item.get("final_weight"),
        (
            item["claim_confidence"]
            + item["time_relevance"]
            + item["source_quality_weight"]
            + item["relevance_weight"]
            + item["freshness_weight"]
        )
        / 5.0,
    )
    item["direction"] = _claim_direction_from_text(item.get("direction"))
    item["explanation"] = _clean_text(item.get("explanation"))

    signed_weight = _safe_float(item.get("signed_weight"))
    if signed_weight is None:
        if item["direction"] == "pro":
            signed_weight = item["final_weight"]
        elif item["direction"] == "contra":
            signed_weight = -item["final_weight"]
        else:
            signed_weight = 0.0
    item["signed_weight"] = float(signed_weight)

    return item


def _fallback_research_sources(question_text: str, max_sources: int) -> list[dict[str, Any]]:
    return [
        {
            "title": f"Question context: {question_text[:120]}",
            "url": None,
            "domain": "internal",
            "published_at": None,
            "excerpt": question_text,
            "summary": "Fallback source created from the question text because no research backend was available.",
            "relevance_score": 0.50,
            "weight": 0.50,
            "source_type": "fallback",
        }
    ][:max_sources]


def _fallback_extract_claims(question_text: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "claim_text": f"The available information around '{question_text}' is limited, so the forecast remains close to the base rate.",
            "claim_type": "uncertainty",
            "source_url": sources[0].get("url") if sources else None,
            "source_title": sources[0].get("title") if sources else "Fallback source",
            "source_type": sources[0].get("source_type") if sources else "fallback",
            "claim_confidence": 0.45,
            "time_relevance": 0.50,
            "source_quality_weight": 0.50,
            "relevance_weight": 0.50,
            "freshness_weight": 0.50,
            "final_weight": 0.45,
            "direction": "uncertain",
            "signed_weight": 0.0,
            "explanation": "Generated by fallback extraction because no dedicated claim extraction backend was available.",
        }
    ]


def _call_research_sources(question_text: str, session: Any, config: EngineConfig) -> list[dict[str, Any]]:
    if _research_sources is None:
        return _fallback_research_sources(question_text, config.max_sources)

    try:
        result = _research_sources(question_text, session=session, max_sources=config.max_sources)
    except TypeError:
        try:
            result = _research_sources(question_text, session=session)
        except TypeError:
            result = _research_sources(question_text)
    except Exception:
        return _fallback_research_sources(question_text, config.max_sources)

    if not result:
        return _fallback_research_sources(question_text, config.max_sources)

    normalized = [_source_to_dict(item) for item in list(result)[: config.max_sources]]
    return normalized or _fallback_research_sources(question_text, config.max_sources)


def _call_extract_claims(question_text: str, sources: list[dict[str, Any]], session: Any) -> list[dict[str, Any]]:
    if _extract_claims is None:
        return _fallback_extract_claims(question_text, sources)

    try:
        result = _extract_claims(question_text, sources=sources, session=session)
    except TypeError:
        try:
            result = _extract_claims(question_text, sources=sources)
        except TypeError:
            try:
                result = _extract_claims(question_text, sources)
            except Exception:
                return _fallback_extract_claims(question_text, sources)
    except Exception:
        return _fallback_extract_claims(question_text, sources)

    if not result:
        return _fallback_extract_claims(question_text, sources)

    return [_claim_to_dict(item) for item in result]


def _call_score_claims(claims: list[dict[str, Any]], question_text: str, session: Any) -> list[dict[str, Any]]:
    if _score_claims is None:
        return [_claim_to_dict(item) for item in claims]

    try:
        result = _score_claims(question_text, claims=claims, session=session)
    except TypeError:
        try:
            result = _score_claims(claims=claims, session=session)
        except TypeError:
            try:
                result = _score_claims(claims)
            except Exception:
                return [_claim_to_dict(item) for item in claims]
    except Exception:
        return [_claim_to_dict(item) for item in claims]

    if not result:
        return [_claim_to_dict(item) for item in claims]

    return [_claim_to_dict(item) for item in result]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _compute_probability_from_claims(
    claims: list[dict[str, Any]],
    prior_probability: float = 0.50,
) -> tuple[float, dict[str, Any]]:
    prior = _clamp(prior_probability, 0.0, 1.0)

    if not claims:
        return (
            prior,
            {
                "prior_probability": prior,
                "claim_count": 0,
                "pro_weight_sum": 0.0,
                "contra_weight_sum": 0.0,
                "uncertain_weight_sum": 0.0,
                "net_signal": 0.0,
                "method": "prior_only",
            },
        )

    pro_weight_sum = 0.0
    contra_weight_sum = 0.0
    uncertain_weight_sum = 0.0

    for claim in claims:
        signed_weight = _safe_float(claim.get("signed_weight"), 0.0) or 0.0
        final_weight = _normalize_score(claim.get("final_weight"), 0.5)

        if signed_weight > 0:
            pro_weight_sum += abs(signed_weight)
        elif signed_weight < 0:
            contra_weight_sum += abs(signed_weight)
        else:
            uncertain_weight_sum += final_weight

    net_signal = pro_weight_sum - contra_weight_sum

    evidence_strength = net_signal / max(1.0, len(claims) * 0.60)
    prior_logit = math.log(max(1e-6, prior) / max(1e-6, 1.0 - prior))
    combined_logit = prior_logit + evidence_strength
    probability = _clamp(_sigmoid(combined_logit), 0.0, 1.0)

    diagnostics = {
        "prior_probability": round(prior, 6),
        "claim_count": len(claims),
        "pro_weight_sum": round(pro_weight_sum, 6),
        "contra_weight_sum": round(contra_weight_sum, 6),
        "uncertain_weight_sum": round(uncertain_weight_sum, 6),
        "net_signal": round(net_signal, 6),
        "evidence_strength": round(evidence_strength, 6),
        "method": "weighted_claim_signal",
    }
    return probability, diagnostics


def _compute_confidence(claims: list[dict[str, Any]], config: EngineConfig) -> float:
    if not claims:
        return config.min_confidence

    avg_weight = sum(_normalize_score(c.get("final_weight"), 0.5) for c in claims) / len(claims)
    avg_claim_conf = sum(_normalize_score(c.get("claim_confidence"), 0.5) for c in claims) / len(claims)
    directional_share = sum(1 for c in claims if c.get("direction") in {"pro", "contra"}) / max(1, len(claims))

    combined = (avg_weight * 0.45) + (avg_claim_conf * 0.35) + (directional_share * 0.20)
    return _clamp(combined, config.min_confidence, config.max_confidence)


def _sort_claims_by_magnitude(claims: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        claims,
        key=lambda c: (
            abs(_safe_float(c.get("signed_weight"), 0.0) or 0.0),
            _normalize_score(c.get("final_weight"), 0.0),
        ),
        reverse=True,
    )


def _top_claim_buckets(
    claims: list[dict[str, Any]],
    per_bucket: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pro = _sort_claims_by_magnitude([c for c in claims if c.get("direction") == "pro"])[:per_bucket]
    contra = _sort_claims_by_magnitude([c for c in claims if c.get("direction") == "contra"])[:per_bucket]
    uncertainties = _sort_claims_by_magnitude([c for c in claims if c.get("direction") == "uncertain"])[:per_bucket]
    return pro, contra, uncertainties


def _format_pct(probability_01: Optional[float]) -> str:
    if probability_01 is None:
        return "—"
    return f"{round(probability_01 * 100.0, 1)}%"


def _probability_bucket(probability_01: Optional[float]) -> str:
    if probability_01 is None:
        return "unknown"
    if probability_01 >= 0.70:
        return "likely_yes"
    if probability_01 >= 0.60:
        return "lean_yes"
    if probability_01 > 0.40:
        return "uncertain"
    if probability_01 > 0.30:
        return "lean_no"
    return "likely_no"


def _strip_question_prefix(question_text: str) -> str:
    q = _clean_text(question_text, "this question")
    q = re.sub(r"^[\"'„“]+|[\"'“”]+$", "", q).strip()
    return q


def _normalize_question_clause(question_text: str) -> str:
    q = _strip_question_prefix(question_text)
    q = re.sub(r"\?$", "", q).strip()
    q_lower = q.lower()

    replacements = [
        (r"^wird\s+", "dass "),
        (r"^werden\s+", "dass "),
        (r"^warum\s+", ""),
        (r"^wann\s+", ""),
        (r"^wie\s+", ""),
        (r"^ob\s+", "ob "),
        (r"^kommt es\s+", "dass es "),
        (r"^gibt es\s+", "dass es "),
        (r"^ist\s+", "dass "),
        (r"^sind\s+", "dass "),
        (r"^kann\s+", "dass "),
        (r"^könnte\s+", "dass "),
        (r"^dürfte\s+", "dass "),
        (r"^muss\s+", "dass "),
        (r"^hat\s+", "dass "),
        (r"^haben\s+", "dass "),
    ]

    for pattern, replacement in replacements:
        if re.match(pattern, q_lower):
            q = re.sub(pattern, replacement, q, flags=re.IGNORECASE)
            break

    q = q.strip()
    if not q:
        return "dass dies eintritt"

    if not q.lower().startswith(("dass ", "ob ")):
        q = f"dass {q[0].lower()}{q[1:]}" if len(q) > 1 else f"dass {q.lower()}"

    return q


def _question_answer_phrase(question_text: str, bucket: str) -> str:
    q_raw = _strip_question_prefix(question_text)
    q_clause = _normalize_question_clause(question_text)
    q_lower = q_raw.lower()

    if q_lower.startswith("wird "):
        subject = re.sub(r"^wird\s+", "", q_raw, flags=re.IGNORECASE).rstrip("?").strip()
        if bucket in {"likely_yes", "lean_yes"}:
            return f"Derzeit ist es eher wahrscheinlich, dass {subject}."
        if bucket in {"likely_no", "lean_no"}:
            return f"Derzeit ist es eher unwahrscheinlich, dass {subject}."
        return f"Ob {subject}, ist derzeit offen."

    if q_lower.startswith("werden "):
        subject = re.sub(r"^werden\s+", "", q_raw, flags=re.IGNORECASE).rstrip("?").strip()
        if bucket in {"likely_yes", "lean_yes"}:
            return f"Derzeit ist es eher wahrscheinlich, dass {subject}."
        if bucket in {"likely_no", "lean_no"}:
            return f"Derzeit ist es eher unwahrscheinlich, dass {subject}."
        return f"Ob {subject}, ist derzeit offen."

    if q_lower.startswith("kommt es "):
        subject = re.sub(r"^kommt es\s+", "", q_raw, flags=re.IGNORECASE).rstrip("?").strip()
        if bucket in {"likely_yes", "lean_yes"}:
            return f"Derzeit ist es eher wahrscheinlich, dass es {subject}."
        if bucket in {"likely_no", "lean_no"}:
            return f"Derzeit ist es eher unwahrscheinlich, dass es {subject}."
        return f"Ob es {subject}, ist derzeit offen."

    if q_lower.startswith("gibt es "):
        subject = re.sub(r"^gibt es\s+", "", q_raw, flags=re.IGNORECASE).rstrip("?").strip()
        if bucket in {"likely_yes", "lean_yes"}:
            return f"Derzeit ist es eher wahrscheinlich, dass es {subject}."
        if bucket in {"likely_no", "lean_no"}:
            return f"Derzeit ist es eher unwahrscheinlich, dass es {subject}."
        return f"Ob es {subject}, ist derzeit offen."

    if q_lower.startswith("ist "):
        subject = re.sub(r"^ist\s+", "", q_raw, flags=re.IGNORECASE).rstrip("?").strip()
        if bucket in {"likely_yes", "lean_yes"}:
            return f"Derzeit spricht mehr dafür, dass {subject}."
        if bucket in {"likely_no", "lean_no"}:
            return f"Derzeit spricht mehr dagegen, dass {subject}."
        return f"Ob {subject}, ist derzeit offen."

    if q_lower.startswith("sind "):
        subject = re.sub(r"^sind\s+", "", q_raw, flags=re.IGNORECASE).rstrip("?").strip()
        if bucket in {"likely_yes", "lean_yes"}:
            return f"Derzeit spricht mehr dafür, dass {subject}."
        if bucket in {"likely_no", "lean_no"}:
            return f"Derzeit spricht mehr dagegen, dass {subject}."
        return f"Ob {subject}, ist derzeit offen."

    if bucket in {"likely_yes", "lean_yes"}:
        return f"Derzeit ist es eher wahrscheinlich, {q_clause}."
    if bucket in {"likely_no", "lean_no"}:
        return f"Derzeit ist es eher unwahrscheinlich, {q_clause}."
    return f"{q_raw} ist derzeit noch nicht klar zu beantworten."


def build_direct_answer(
    question_text: Optional[str],
    probability: Optional[float],
) -> dict[str, Any]:
    q = _clean_text(question_text, "this question")
    p = _normalize_probability_value(probability)
    bucket = _probability_bucket(p)

    if p is None:
        return {
            "direct_answer": f'Die Frage "{q}" lässt sich derzeit noch nicht belastbar beantworten.',
            "answer_label": "unknown",
            "answer_confidence_band": "unknown",
            "answer_rationale_short": "No usable probability was available.",
        }

    pct = round(p * 100.0, 1)
    natural_answer = _question_answer_phrase(q, bucket)

    if bucket == "likely_yes":
        return {
            "direct_answer": f"{natural_answer} Aktuelle Wahrscheinlichkeit: {pct}%.",
            "answer_label": "yes",
            "answer_confidence_band": "likely",
            "answer_rationale_short": f"Die aktuelle Wahrscheinlichkeit liegt mit {pct}% klar über der Ja-Schwelle.",
        }

    if bucket == "lean_yes":
        return {
            "direct_answer": f"{natural_answer} Aktuelle Wahrscheinlichkeit: {pct}%.",
            "answer_label": "lean_yes",
            "answer_confidence_band": "moderate",
            "answer_rationale_short": f"Die aktuelle Wahrscheinlichkeit liegt mit {pct}% leicht über 50%.",
        }

    if bucket == "uncertain":
        return {
            "direct_answer": f"{natural_answer} Aktuelle Wahrscheinlichkeit: {pct}%.",
            "answer_label": "uncertain",
            "answer_confidence_band": "close_call",
            "answer_rationale_short": f"Die aktuelle Wahrscheinlichkeit liegt mit {pct}% zu nah an 50/50 für eine klare Richtung.",
        }

    if bucket == "lean_no":
        return {
            "direct_answer": f"{natural_answer} Aktuelle Wahrscheinlichkeit: {pct}%.",
            "answer_label": "lean_no",
            "answer_confidence_band": "moderate",
            "answer_rationale_short": f"Die aktuelle Wahrscheinlichkeit liegt mit {pct}% leicht unter 50%.",
        }

    return {
        "direct_answer": f"{natural_answer} Aktuelle Wahrscheinlichkeit: {pct}%.",
        "answer_label": "no",
        "answer_confidence_band": "unlikely",
        "answer_rationale_short": f"Die aktuelle Wahrscheinlichkeit liegt mit {pct}% klar unter der Nein-Schwelle.",
    }


def _build_summary(
    question_text: str,
    calibrated_probability: Optional[float],
    confidence: float,
    top_pro_claims: list[dict[str, Any]],
    top_contra_claims: list[dict[str, Any]],
    top_uncertainties: list[dict[str, Any]],
) -> str:
    direct = build_direct_answer(question_text, calibrated_probability)
    parts: list[str] = [direct["direct_answer"]]

    parts.append(
        f"Die kalibrierte Eintrittswahrscheinlichkeit liegt aktuell bei {_format_pct(calibrated_probability)} "
        f"bei einer Modell-Confidence von {_format_pct(confidence)}."
    )

    if top_pro_claims:
        parts.append(f"Stärkstes Pro-Signal: {top_pro_claims[0].get('claim_text', '—')}")
    if top_contra_claims:
        parts.append(f"Stärkstes Contra-Signal: {top_contra_claims[0].get('claim_text', '—')}")
    if top_uncertainties:
        parts.append(f"Wichtigste Unsicherheit: {top_uncertainties[0].get('claim_text', '—')}")

    return "\n\n".join(parts)


def _build_explanation_md(
    question_text: str,
    raw_probability: float,
    calibrated_probability: float,
    confidence: float,
    sources: list[dict[str, Any]],
    top_pro_claims: list[dict[str, Any]],
    top_contra_claims: list[dict[str, Any]],
    top_uncertainties: list[dict[str, Any]],
    runtime_calibration_meta: dict[str, Any],
) -> str:
    direct = build_direct_answer(question_text, calibrated_probability)

    lines: list[str] = []
    lines.append("# Forecast")
    lines.append("")
    lines.append(f"**Frage:** {question_text}")
    lines.append("")
    lines.append(f"**Direkte Antwort:** {direct['direct_answer']}")
    lines.append("")
    lines.append(f"- Raw Probability: {_format_pct(raw_probability)}")
    lines.append(f"- Calibrated Probability: {_format_pct(calibrated_probability)}")
    lines.append(f"- Confidence: {_format_pct(confidence)}")
    lines.append("")

    if runtime_calibration_meta:
        lines.append("## Runtime Calibration")
        lines.append("")
        for key, value in runtime_calibration_meta.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    if top_pro_claims:
        lines.append("## Top Pro Claims")
        lines.append("")
        for claim in top_pro_claims:
            lines.append(f"- {claim.get('claim_text', '—')}")
        lines.append("")

    if top_contra_claims:
        lines.append("## Top Contra Claims")
        lines.append("")
        for claim in top_contra_claims:
            lines.append(f"- {claim.get('claim_text', '—')}")
        lines.append("")

    if top_uncertainties:
        lines.append("## Top Uncertainties")
        lines.append("")
        for claim in top_uncertainties:
            lines.append(f"- {claim.get('claim_text', '—')}")
        lines.append("")

    if sources:
        lines.append("## Sources")
        lines.append("")
        for source in sources:
            title = source.get("title") or source.get("url") or "Untitled source"
            url = source.get("url")
            if url:
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {title}")
        lines.append("")

    return "\n".join(lines).strip() or "Forecast generated."


def _get_runtime_calibration_payload(
    session: Any,
    category: Optional[str] = None,
) -> dict[str, Any]:
    if _get_runtime_calibration is None:
        return {
            "enabled": False,
            "record_count": 0,
            "method": "none",
            "notes": ["No calibration_service integration available in current runtime."],
        }

    try:
        payload = _get_runtime_calibration(session=session, category=category)
    except TypeError:
        try:
            payload = _get_runtime_calibration(session=session)
        except Exception:
            payload = None
    except Exception:
        payload = None

    if not payload:
        return {
            "enabled": False,
            "record_count": 0,
            "method": "none",
            "notes": ["Calibration service returned no runtime calibration payload."],
        }

    return dict(payload)


def _apply_runtime_calibration_payload(
    raw_probability: float,
    runtime_calibration_meta: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    if _apply_runtime_calibration is None:
        return raw_probability, {
            "applied": False,
            "reason": "apply_runtime_calibration function not available",
        }

    try:
        calibrated = _apply_runtime_calibration(raw_probability, runtime_calibration_meta)
    except TypeError:
        try:
            calibrated = _apply_runtime_calibration(
                probability=raw_probability,
                calibration=runtime_calibration_meta,
            )
        except Exception:
            calibrated = raw_probability
    except Exception:
        calibrated = raw_probability

    calibrated_probability = _normalize_probability_value(calibrated)
    if calibrated_probability is None:
        calibrated_probability = raw_probability

    signals = {
        "applied": calibrated_probability != raw_probability,
        "raw_probability": round(raw_probability, 6),
        "calibrated_probability": round(calibrated_probability, 6),
    }
    return calibrated_probability, signals


class ForecastEngine:
    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self.config = config or EngineConfig()

    def generate(
        self,
        question: Any,
        session: Any = None,
        *,
        category: Optional[str] = None,
    ) -> dict[str, Any]:
        question_text = _question_text(question)
        category = category or _question_category(question)

        sources = _call_research_sources(question_text, session=session, config=self.config)
        sources = sources[: self.config.max_sources]

        extracted_claims = _call_extract_claims(question_text, sources=sources, session=session)
        scored_claims = _call_score_claims(extracted_claims, question_text=question_text, session=session)
        claims = [_claim_to_dict(item) for item in scored_claims][: self.config.max_claims]

        raw_probability, probability_diagnostics = _compute_probability_from_claims(
            claims,
            prior_probability=self.config.prior_probability,
        )

        runtime_calibration_meta = _get_runtime_calibration_payload(session=session, category=category)
        calibrated_probability, calibration_signals = _apply_runtime_calibration_payload(
            raw_probability=raw_probability,
            runtime_calibration_meta=runtime_calibration_meta,
        )

        confidence = _compute_confidence(claims, config=self.config)
        top_pro_claims, top_contra_claims, top_uncertainties = _top_claim_buckets(
            claims,
            per_bucket=self.config.top_claims_per_bucket,
        )

        summary = _build_summary(
            question_text=question_text,
            calibrated_probability=calibrated_probability,
            confidence=confidence,
            top_pro_claims=top_pro_claims,
            top_contra_claims=top_contra_claims,
            top_uncertainties=top_uncertainties,
        )

        explanation_md = _build_explanation_md(
            question_text=question_text,
            raw_probability=raw_probability,
            calibrated_probability=calibrated_probability,
            confidence=confidence,
            sources=sources,
            top_pro_claims=top_pro_claims,
            top_contra_claims=top_contra_claims,
            top_uncertainties=top_uncertainties,
            runtime_calibration_meta=runtime_calibration_meta,
        )

        effective_probability = calibrated_probability
        direct_answer_payload = build_direct_answer(
            question_text=question_text,
            probability=effective_probability,
        )

        diagnostics: dict[str, Any] = {
            "generated_at": _utcnow_iso(),
            "question_text": question_text,
            "question_category": category,
            "source_count": len(sources),
            "claim_count": len(claims),
            "probability_model": probability_diagnostics,
        }

        return {
            "probability": calibrated_probability,
            "raw_probability": raw_probability,
            "calibrated_probability": calibrated_probability,
            "confidence": confidence,
            "summary": summary,
            "explanation_md": explanation_md,
            "sources": sources,
            "claims": claims,
            "top_pro_claims": top_pro_claims,
            "top_contra_claims": top_contra_claims,
            "top_uncertainties": top_uncertainties,
            "diagnostics": diagnostics,
            "runtime_calibration_meta": runtime_calibration_meta,
            "calibration_signals": calibration_signals,
            "direct_answer": direct_answer_payload["direct_answer"],
            "answer_label": direct_answer_payload["answer_label"],
            "answer_confidence_band": direct_answer_payload["answer_confidence_band"],
            "answer_rationale_short": direct_answer_payload["answer_rationale_short"],
        }


def generate_forecast(
    question: Any,
    session: Any = None,
    *,
    category: Optional[str] = None,
    config: Optional[EngineConfig] = None,
) -> dict[str, Any]:
    engine = ForecastEngine(config=config)
    return engine.generate(question=question, session=session, category=category)


def compute_probability(
    question: Any,
    session: Any = None,
    *,
    category: Optional[str] = None,
    config: Optional[EngineConfig] = None,
) -> dict[str, Any]:
    """
    Backward-compatible convenience entry point.
    Keeps the older function name alive while returning the richer engine payload.
    """
    return generate_forecast(
        question=question,
        session=session,
        category=category,
        config=config,
    )
