from collections import defaultdict
from typing import Any, Dict, List, Tuple
import re


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _claim_text_key(text: str) -> str:
    normalized = _normalize_text(text).lower()
    return re.sub(r"[^a-z0-9äöüß]+", " ", normalized).strip()


def _source_type_weight(source_type: str) -> float:
    return {
        "official": 0.98,
        "wire": 0.92,
        "research": 0.89,
        "major_media": 0.82,
        "other": 0.60,
    }.get((source_type or "other").strip().lower(), 0.60)


def _claim_type_direction(claim_type: str) -> int:
    claim_type = (claim_type or "background").strip().lower()
    if claim_type == "pro":
        return 1
    if claim_type == "contra":
        return -1
    return 0


def _domain_from_url(url: str) -> str:
    match = re.match(r"^https?://([^/]+)", (url or "").strip().lower())
    if not match:
        return ""
    domain = match.group(1)
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _independence_weight(claim: Dict[str, Any], claims: List[Dict[str, Any]]) -> float:
    """
    Downweights sources from the same domain and nearly identical claims.
    """
    source_url = claim.get("source_url", "")
    domain = _domain_from_url(source_url)
    text_key = _claim_text_key(str(claim.get("claim_text", "")))

    same_domain_count = 0
    same_text_count = 0

    for other in claims:
        other_domain = _domain_from_url(str(other.get("source_url", "")))
        other_text_key = _claim_text_key(str(other.get("claim_text", "")))

        if other_domain and other_domain == domain:
            same_domain_count += 1
        if other_text_key and other_text_key == text_key:
            same_text_count += 1

    domain_penalty = min(0.30, max(0, same_domain_count - 1) * 0.08)
    text_penalty = min(0.35, max(0, same_text_count - 1) * 0.12)

    return round(_clamp(1.0 - domain_penalty - text_penalty, 0.35, 1.0), 4)


def _specificity_weight(claim_text: str) -> float:
    text = _normalize_text(claim_text)
    if not text:
        return 0.4

    score = 0.45

    if len(text) >= 50:
        score += 0.10
    if re.search(r"\b\d{4}\b", text):
        score += 0.08
    if re.search(r"\b\d+(\.\d+)?%?\b", text):
        score += 0.06
    if any(token in text.lower() for token in ["according to", "reported", "confirmed", "announced", "stated"]):
        score += 0.06
    if any(token in text.lower() for token in ["official", "commission", "government", "ministry", "nato", "un", "eu"]):
        score += 0.05

    return round(_clamp(score), 4)


def _compute_final_weight(claim: Dict[str, Any], claims: List[Dict[str, Any]]) -> Dict[str, float]:
    source_type = str(claim.get("source_type", "other"))
    claim_confidence = float(claim.get("claim_confidence", 0.5))
    time_relevance = float(claim.get("time_relevance", 0.5))
    source_quality = _source_type_weight(source_type)
    relevance_weight = float(claim.get("relevance_score", 0.5)) if "relevance_score" in claim else 0.5
    freshness_weight = float(claim.get("freshness_score", 0.5)) if "freshness_score" in claim else 0.5
    independence_weight = _independence_weight(claim, claims)
    specificity_weight = _specificity_weight(str(claim.get("claim_text", "")))

    final_weight = (
        source_quality * 0.22
        + claim_confidence * 0.24
        + time_relevance * 0.14
        + relevance_weight * 0.14
        + freshness_weight * 0.10
        + independence_weight * 0.10
        + specificity_weight * 0.06
    )

    return {
        "source_quality_weight": round(source_quality, 4),
        "claim_confidence_weight": round(claim_confidence, 4),
        "time_relevance_weight": round(time_relevance, 4),
        "relevance_weight": round(relevance_weight, 4),
        "freshness_weight": round(freshness_weight, 4),
        "independence_weight": round(independence_weight, 4),
        "specificity_weight": round(specificity_weight, 4),
        "final_weight": round(_clamp(final_weight), 4),
    }


def _merge_duplicate_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merges identical claim texts of the same type and keeps strongest source support.
    """
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for claim in claims:
        key = (
            _claim_text_key(str(claim.get("claim_text", ""))),
            str(claim.get("claim_type", "background")).strip().lower(),
        )
        grouped[key].append(claim)

    merged: List[Dict[str, Any]] = []

    for (_text_key, claim_type), items in grouped.items():
        items_sorted = sorted(
            items,
            key=lambda c: (
                float(c.get("claim_confidence", 0.0)),
                float(c.get("time_relevance", 0.0)),
            ),
            reverse=True,
        )
        best = dict(items_sorted[0])

        supporting_sources = []
        supporting_domains = set()

        for item in items_sorted:
            source_url = str(item.get("source_url", "")).strip()
            source_title = str(item.get("source_title", "")).strip()
            source_type = str(item.get("source_type", "other")).strip()
            domain = _domain_from_url(source_url)

            supporting_sources.append(
                {
                    "source_url": source_url,
                    "source_title": source_title,
                    "source_type": source_type,
                }
            )
            if domain:
                supporting_domains.add(domain)

        best["supporting_sources"] = supporting_sources
        best["supporting_source_count"] = len(supporting_sources)
        best["supporting_domain_count"] = len(supporting_domains)
        best["claim_type"] = claim_type

        merged.append(best)

    return merged


def score_claims(
    claims: List[Dict[str, Any]],
    *,
    max_claims_per_bucket: int = 5,
) -> Dict[str, Any]:
    """
    Input:
      list of claims from claim_extraction.py

    Output:
      - scored_claims
      - top_pro_claims
      - top_contra_claims
      - top_uncertainties
      - top_background
      - net_signal
      - diagnostics
    """
    if not claims:
        return {
            "scored_claims": [],
            "top_pro_claims": [],
            "top_contra_claims": [],
            "top_uncertainties": [],
            "top_background": [],
            "net_signal": 0.0,
            "diagnostics": {
                "claim_count_input": 0,
                "claim_count_scored": 0,
                "pro_weight_sum": 0.0,
                "contra_weight_sum": 0.0,
                "uncertainty_weight_sum": 0.0,
                "background_weight_sum": 0.0,
            },
        }

    merged_claims = _merge_duplicate_claims(claims)

    scored_claims: List[Dict[str, Any]] = []
    pro_weight_sum = 0.0
    contra_weight_sum = 0.0
    uncertainty_weight_sum = 0.0
    background_weight_sum = 0.0

    for claim in merged_claims:
        weights = _compute_final_weight(claim, merged_claims)
        claim_type = str(claim.get("claim_type", "background")).strip().lower()
        direction = _claim_type_direction(claim_type)

        support_boost = min(0.15, max(0, int(claim.get("supporting_domain_count", 1)) - 1) * 0.04)
        final_weight = round(_clamp(weights["final_weight"] + support_boost), 4)

        scored = {
            **claim,
            **weights,
            "support_boost": round(support_boost, 4),
            "final_weight": final_weight,
            "direction": direction,
            "signed_weight": round(final_weight * direction, 4),
        }
        scored_claims.append(scored)

        if claim_type == "pro":
            pro_weight_sum += final_weight
        elif claim_type == "contra":
            contra_weight_sum += final_weight
        elif claim_type == "uncertainty":
            uncertainty_weight_sum += final_weight
        else:
            background_weight_sum += final_weight

    scored_claims = sorted(
        scored_claims,
        key=lambda c: (
            float(c.get("final_weight", 0.0)),
            float(c.get("claim_confidence", 0.0)),
            float(c.get("time_relevance", 0.0)),
        ),
        reverse=True,
    )

    top_pro_claims = [c for c in scored_claims if c.get("claim_type") == "pro"][:max_claims_per_bucket]
    top_contra_claims = [c for c in scored_claims if c.get("claim_type") == "contra"][:max_claims_per_bucket]
    top_uncertainties = [c for c in scored_claims if c.get("claim_type") == "uncertainty"][:max_claims_per_bucket]
    top_background = [c for c in scored_claims if c.get("claim_type") == "background"][:max_claims_per_bucket]

    raw_net = pro_weight_sum - contra_weight_sum
    uncertainty_drag = min(0.35, uncertainty_weight_sum * 0.10)
    net_signal = round(raw_net * (1.0 - uncertainty_drag), 4)

    diagnostics = {
        "claim_count_input": len(claims),
        "claim_count_merged": len(merged_claims),
        "claim_count_scored": len(scored_claims),
        "pro_weight_sum": round(pro_weight_sum, 4),
        "contra_weight_sum": round(contra_weight_sum, 4),
        "uncertainty_weight_sum": round(uncertainty_weight_sum, 4),
        "background_weight_sum": round(background_weight_sum, 4),
        "uncertainty_drag": round(uncertainty_drag, 4),
    }

    return {
        "scored_claims": scored_claims,
        "top_pro_claims": top_pro_claims,
        "top_contra_claims": top_contra_claims,
        "top_uncertainties": top_uncertainties,
        "top_background": top_background,
        "net_signal": net_signal,
        "diagnostics": diagnostics,
    }
