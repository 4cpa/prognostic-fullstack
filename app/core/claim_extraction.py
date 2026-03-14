from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List, Optional


CLAIM_TYPES = {"pro", "contra", "uncertainty", "background"}


@dataclass
class ExtractedClaim:
    claim_text: str
    claim_type: str
    source_url: str
    source_title: str
    source_type: str
    claim_confidence: float
    time_relevance: float


def _normalize_text(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _lower(text: Optional[str]) -> str:
    return _normalize_text(text).lower()


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _split_sentences(text: str) -> List[str]:
    text = _normalize_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?\;\:])\s+", text)
    return [p.strip(" -•\t\r\n") for p in parts if p.strip()]


def _combine_source_text(source: Dict[str, Any]) -> str:
    title = _normalize_text(source.get("title", ""))
    summary = _normalize_text(source.get("summary", ""))
    return _normalize_text(f"{title}. {summary}")


def _question_tokens(question_text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9äöüß\-]{3,}", _lower(question_text))


def _keyword_overlap(question_text: str, text: str) -> float:
    q_tokens = set(_question_tokens(question_text))
    if not q_tokens:
        return 0.3

    t_tokens = set(re.findall(r"[a-zA-Z0-9äöüß\-]{3,}", _lower(text)))
    if not t_tokens:
        return 0.2

    overlap = len(q_tokens.intersection(t_tokens))
    denom = max(4, min(len(q_tokens), 16))
    return _clamp(overlap / denom, 0.0, 1.0)


def _infer_claim_type(question_text: str, sentence: str, fallback_stance: str) -> str:
    text = _lower(sentence)
    q = _lower(question_text)

    pro_terms = [
        "collapse", "breakup", "disintegration", "fracture", "withdrawal", "exit",
        "war", "escalation", "mobilization", "offensive", "crisis", "sanctions shock",
        "default", "recession", "bank run", "conflict", "attack", "invasion",
        "zerbrechen", "zerfall", "krieg", "eskalation", "krise", "angriff", "invasion",
    ]
    contra_terms = [
        "stability", "stable", "continuity", "agreement", "unity", "cooperation",
        "ceasefire", "de-escalation", "institutional continuity", "support package",
        "reaffirmed commitment", "resilience", "integration",
        "stabilität", "einigung", "zusammenhalt", "waffenstillstand", "deeskalation",
        "kontinuität", "unterstützung", "integration",
    ]
    uncertainty_terms = [
        "may", "might", "could", "risk", "warning", "concern", "uncertain",
        "volatility", "tension", "scenario", "possible", "unlikely", "likely",
        "könnte", "risiko", "warnung", "sorge", "unsicher", "spannung", "szenario",
        "möglich", "wahrscheinlich", "unwahrscheinlich",
    ]

    pro_hits = sum(1 for term in pro_terms if term in text)
    contra_hits = sum(1 for term in contra_terms if term in text)
    uncertainty_hits = sum(1 for term in uncertainty_terms if term in text)

    if ("weltkrieg" in q or "world war" in q) and ("ceasefire" in text or "de-escalation" in text):
        contra_hits += 1
    if ("eu" in q or "european union" in q) and ("unity" in text or "integration" in text):
        contra_hits += 1
    if ("eu" in q or "european union" in q) and ("withdrawal" in text or "exit" in text or "fracture" in text):
        pro_hits += 1

    if pro_hits > contra_hits and pro_hits >= 1:
        return "pro"
    if contra_hits > pro_hits and contra_hits >= 1:
        return "contra"
    if uncertainty_hits >= 1:
        return "uncertainty"
    if fallback_stance in CLAIM_TYPES:
        return fallback_stance
    return "background"


def _claim_confidence(
    *,
    question_text: str,
    sentence: str,
    source: Dict[str, Any],
    claim_type: str,
) -> float:
    source_type = str(source.get("source_type", "other"))
    relevance = float(source.get("relevance_score", 0.4))
    credibility = float(source.get("credibility_score", 0.6))
    freshness = float(source.get("freshness_score", 0.45))
    overall = float(source.get("overall_score", 0.5))

    overlap = _keyword_overlap(question_text, sentence)
    length_bonus = 0.05 if len(sentence) >= 40 else 0.0
    type_bonus = {
        "official": 0.08,
        "wire": 0.06,
        "research": 0.05,
        "major_media": 0.03,
        "other": 0.0,
    }.get(source_type, 0.0)

    claim_type_bonus = {
        "pro": 0.04,
        "contra": 0.04,
        "uncertainty": 0.02,
        "background": 0.0,
    }.get(claim_type, 0.0)

    score = (
        relevance * 0.30
        + credibility * 0.25
        + freshness * 0.10
        + overall * 0.20
        + overlap * 0.10
        + length_bonus
        + type_bonus
        + claim_type_bonus
    )
    return round(_clamp(score), 4)


def _time_relevance(question_text: str, sentence: str, source: Dict[str, Any]) -> float:
    text = _lower(f"{question_text} {sentence}")
    freshness = float(source.get("freshness_score", 0.45))
    score = freshness * 0.7 + 0.2

    if "2026" in text or "2027" in text or "this year" in text or "next year" in text:
        score += 0.08
    if "today" in text or "current" in text or "currently" in text or "ongoing" in text:
        score += 0.06
    if "historical" in text or "history" in text or "past decade" in text:
        score -= 0.08

    return round(_clamp(score), 4)


def _dedupe_claims(claims: List[ExtractedClaim]) -> List[ExtractedClaim]:
    seen = set()
    deduped: List[ExtractedClaim] = []

    for claim in sorted(
        claims,
        key=lambda c: (c.claim_confidence, c.time_relevance, len(c.claim_text)),
        reverse=True,
    ):
        key = (
            re.sub(r"[^a-z0-9äöüß]+", " ", claim.claim_text.lower()).strip(),
            claim.source_url.strip().lower(),
            claim.claim_type,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(claim)

    return deduped


def extract_claims_from_source(
    question_text: str,
    source: Dict[str, Any],
    *,
    max_claims_per_source: int = 3,
) -> List[Dict[str, Any]]:
    source_url = _normalize_text(source.get("url", ""))
    source_title = _normalize_text(source.get("title", ""))
    source_type = _normalize_text(source.get("source_type", "other")) or "other"
    fallback_stance = _normalize_text(source.get("stance", "background")) or "background"

    combined_text = _combine_source_text(source)
    if not combined_text:
        return []

    sentences = _split_sentences(combined_text)
    if not sentences:
        sentences = [combined_text]

    claims: List[ExtractedClaim] = []

    for sentence in sentences:
        if len(sentence) < 20:
            continue

        claim_type = _infer_claim_type(question_text, sentence, fallback_stance)
        claim_confidence = _claim_confidence(
            question_text=question_text,
            sentence=sentence,
            source=source,
            claim_type=claim_type,
        )
        time_relevance = _time_relevance(question_text, sentence, source)

        claims.append(
            ExtractedClaim(
                claim_text=sentence,
                claim_type=claim_type,
                source_url=source_url,
                source_title=source_title,
                source_type=source_type,
                claim_confidence=claim_confidence,
                time_relevance=time_relevance,
            )
        )

    claims = _dedupe_claims(claims)
    claims = claims[:max_claims_per_source]

    return [asdict(c) for c in claims]


def extract_claims_from_sources(
    question_text: str,
    sources: List[Dict[str, Any]],
    *,
    max_claims_per_source: int = 3,
    max_total_claims: int = 30,
) -> Dict[str, Any]:
    all_claims: List[ExtractedClaim] = []

    for source in sources:
        extracted = extract_claims_from_source(
            question_text,
            source,
            max_claims_per_source=max_claims_per_source,
        )
        for item in extracted:
            all_claims.append(ExtractedClaim(**item))

    deduped = _dedupe_claims(all_claims)
    deduped = sorted(
        deduped,
        key=lambda c: (c.claim_confidence * 0.75 + c.time_relevance * 0.25),
        reverse=True,
    )[:max_total_claims]

    counts = {
        "pro": 0,
        "contra": 0,
        "uncertainty": 0,
        "background": 0,
    }
    for claim in deduped:
        counts[claim.claim_type] = counts.get(claim.claim_type, 0) + 1

    return {
        "question_text": question_text,
        "claims": [asdict(c) for c in deduped],
        "claim_counts": counts,
    }
