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
    excerpt = _normalize_text(source.get("excerpt", ""))
    return _normalize_text(f"{title}. {summary}. {excerpt}")


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


def _question_kind(question_text: str) -> str:
    q = _lower(question_text)

    if "weltkrieg" in q or "world war" in q:
        return "world_war"
    if "eu zer" in q or "eu breakup" in q or "european union breakup" in q:
        return "eu_breakup"
    if ("staat" in q or "state" in q) and ("kollaps" in q or "collapse" in q):
        return "state_collapse"
    if "krieg" in q or "war" in q or "conflict" in q:
        return "war"
    # Fortbestand-Fragen: "Besteht X fort?", "Wird X weiterbestehen?", etc.
    if (
        " fort?" in q or " fort " in q
        or "fortbestand" in q or "fortbestehen" in q
        or "weiterbestehen" in q or "überleben" in q
        or "dissolution" in q or "still exist" in q
        or "bleibt bestehen" in q
    ):
        return "existence"
    return "general"


def _contains_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _infer_claim_type(question_text: str, sentence: str, fallback_stance: str) -> str:
    text = _lower(sentence)
    q_kind = _question_kind(question_text)

    pro_terms = [
        "collapse",
        "breakup",
        "disintegration",
        "fracture",
        "withdrawal",
        "exit",
        "war",
        "escalation",
        "mobilization",
        "offensive",
        "crisis",
        "sanctions shock",
        "default",
        "bank run",
        "conflict",
        "attack",
        "invasion",
        "zerbrechen",
        "zerfall",
        "krieg",
        "eskalation",
        "krise",
        "angriff",
        "invasion",
    ]
    contra_terms = [
        "stability",
        "stable",
        "continuity",
        "agreement",
        "unity",
        "cooperation",
        "ceasefire",
        "de-escalation",
        "institutional continuity",
        "support package",
        "reaffirmed commitment",
        "resilience",
        "integration",
        "containment",
        "restraint",
        "stabilität",
        "einigung",
        "zusammenhalt",
        "waffenstillstand",
        "deeskalation",
        "kontinuität",
        "unterstützung",
        "integration",
        "eindämmung",
        "zurückhaltung",
    ]
    uncertainty_terms = [
        "may",
        "might",
        "could",
        "risk",
        "warning",
        "concern",
        "uncertain",
        "volatility",
        "tension",
        "scenario",
        "possible",
        "unlikely",
        "likely",
        "könnte",
        "risiko",
        "warnung",
        "sorge",
        "unsicher",
        "spannung",
        "szenario",
        "möglich",
        "wahrscheinlich",
        "unwahrscheinlich",
    ]

    pro_hits = sum(1 for term in pro_terms if term in text)
    contra_hits = sum(1 for term in contra_terms if term in text)
    uncertainty_hits = sum(1 for term in uncertainty_terms if term in text)

    if q_kind == "existence":
        # Pro: Institution ist aktiv, plant Zukunft → unterstützt Fortbestand
        existence_pro = [
            "hosts", "convenes", "holds conference", "scheduled", "plans",
            "operational", "continues", "renewed", "strengthened",
            "budget approved", "member states", "general assembly", "security council",
            "session", "summit", "annual meeting", "conference", "treaty",
            "aktiv", "weiterhin", "fortsetzt", "veranstaltet", "tagt",
        ]
        # Contra: Bedrohung, Rückzug, Kollaps → gefährdet Fortbestand
        existence_contra = [
            "collapse", "financial collapse", "dissolution", "disbanded",
            "disbands", "defunds", "funding cut", "withdraws from", "exit",
            "leaves", "quits", "ineffective", "obsolete", "abolished",
            "paralyzed", "in danger", "financial crisis", "debt", "unpaid dues",
            "auflösung", "kollaps", "finanzierungskrise", "austritt",
        ]
        if _contains_any(text, existence_contra):
            return "contra"
        if _contains_any(text, existence_pro):
            return "pro"
        if uncertainty_hits >= 1:
            return "uncertainty"
        if fallback_stance in CLAIM_TYPES:
            return fallback_stance
        return "background"

    if q_kind == "world_war":
        direct_world_war_pro = [
            "world war",
            "weltkrieg",
            "global war",
            "great power war",
            "major power war",
            "nato article 5",
            "article 5",
            "direct conflict between major powers",
            "direct u.s.-russia conflict",
            "direct us-russia conflict",
            "direct u.s.-china conflict",
            "direct us-china conflict",
            "multiple major powers at war",
            "broader war involving major powers",
            "global military conflict",
        ]

        diplomatic_contra = [
            "ceasefire",
            "ceasefire talks",
            "de-escalation",
            "containment",
            "limited response",
            "conflict remains regional",
            "no broader war",
            "talks with iran",
            "held talks with iran",
            "diplomatic channel",
            "negotiation",
            "negotiations",
            "diplomatic push",
            "backchannel",
            "restraint",
            "avoid wider war",
            "diplomatic efforts",
            "peace talks",
            "mediation",
            "mediated talks",
            "indirect talks",
            "resume talks",
            "reopen talks",
        ]

        military_uncertainty = [
            "ground assault",
            "red sea shipping route",
            "shipping route",
            "hormuz",
            "strait of hormuz",
            "missile",
            "missiles",
            "retaliation",
            "new front",
            "open new front",
            "airstrike",
            "airstrikes",
            "nuclear site",
            "houthi",
            "houthis",
            "military escalation",
            "widening conflict",
            "conflict widens",
            "enters second month",
            "intercept missiles",
            "launch israel strike",
            "war with israel and the united states",
            "global conflict tracker",
            "regional escalation",
            "regional war",
            "broader regional war",
            "shipping disruption",
            "naval escort",
            "warship escorts",
            "more strikes",
            "additional strikes",
            "fresh strikes",
            "new strikes",
            "troop buildup",
            "troop deployment",
            "mobilization",
        ]

        if _contains_any(text, direct_world_war_pro):
            return "pro"

        if _contains_any(text, diplomatic_contra):
            return "contra"

        if _contains_any(text, military_uncertainty):
            return "uncertainty"

        if uncertainty_hits >= 1:
            return "uncertainty"

        return "background"

    if q_kind == "eu_breakup":
        direct_eu_breakup_pro = [
            "leave the eu",
            "withdrawal from the eu",
            "eu exit",
            "member state exit",
            "european union breakup",
            "eu disintegration",
        ]
        direct_eu_breakup_contra = [
            "unity",
            "integration",
            "reaffirmed commitment",
            "institutional continuity",
            "support package",
        ]

        if _contains_any(text, direct_eu_breakup_pro):
            return "pro"
        if _contains_any(text, direct_eu_breakup_contra):
            return "contra"

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
        "national_media": 0.02,
        "other": 0.0,
        "alternative": -0.05,
    }.get(source_type, 0.0)

    claim_type_bonus = {
        "pro": 0.04,
        "contra": 0.04,
        "uncertainty": 0.02,
        "background": 0.0,
    }.get(claim_type, 0.0)

    q_kind = _question_kind(question_text)
    text = _lower(sentence)

    if q_kind == "world_war":
        direct_strong_pro = [
            "world war",
            "weltkrieg",
            "global war",
            "great power war",
            "major power war",
            "article 5",
            "multiple major powers at war",
            "direct us-russia conflict",
            "direct u.s.-russia conflict",
            "direct us-china conflict",
            "direct u.s.-china conflict",
        ]

        diplomatic_contra = [
            "ceasefire",
            "ceasefire talks",
            "de-escalation",
            "containment",
            "talks with iran",
            "held talks with iran",
            "diplomatic channel",
            "negotiation",
            "negotiations",
            "backchannel",
            "avoid wider war",
            "conflict remains regional",
            "no broader war",
            "peace talks",
            "mediation",
            "indirect talks",
            "diplomatic efforts",
        ]

        military_uncertainty = [
            "ground assault",
            "hormuz",
            "new front",
            "houthi",
            "houthis",
            "airstrike",
            "airstrikes",
            "missile",
            "missiles",
            "shipping route",
            "red sea",
            "intercept missiles",
            "war with israel and the united states",
            "global conflict tracker",
            "regional escalation",
            "widening conflict",
            "more strikes",
            "fresh strikes",
            "troop buildup",
            "troop deployment",
            "warship escorts",
        ]

        if claim_type == "pro":
            if _contains_any(text, direct_strong_pro):
                claim_type_bonus = 0.04
            else:
                claim_type_bonus = 0.01

        if claim_type == "contra":
            if _contains_any(text, diplomatic_contra):
                claim_type_bonus = 0.045
            else:
                claim_type_bonus = 0.025

        if claim_type == "uncertainty":
            if _contains_any(text, military_uncertainty):
                claim_type_bonus = 0.03
            else:
                claim_type_bonus = 0.02

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
    # Regelbasierte Keyword-Extraktion (kein LLM-Call, spart Quota)
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
        if claim_type == "background":
            continue

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
    deduped = deduped[:max_total_claims]

    return {
        "claims": [asdict(c) for c in deduped],
        "count": len(deduped),
    }


def extract_claims(
    question_text: str,
    sources: List[Dict[str, Any]],
    session: Any = None,
) -> List[Dict[str, Any]]:
    result = extract_claims_from_sources(
        question_text,
        sources,
        max_claims_per_source=3,
        max_total_claims=30,
    )
    return result.get("claims", [])
