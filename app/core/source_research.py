from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
import hashlib
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
REQUEST_TIMEOUT = 12


WIRE_PUBLISHER_PATTERNS = (
    "reuters",
    "associated press",
    "ap ",
    "apnews",
    "afp",
    "bloomberg",
)

MAJOR_MEDIA_PUBLISHER_PATTERNS = (
    "dw",
    "dw.com",
    "bbc",
    "cnn",
    "france 24",
    "al jazeera",
    "the guardian",
    "financial times",
    "wsj",
    "wall street journal",
    "new york times",
    "washington post",
    "haaretz",
    "economist",
    "cnbc",
)

AGGREGATOR_PUBLISHER_PATTERNS = (
    "msn",
    "yahoo",
    "aol",
    "newsbreak",
    "flipboard",
    "smartnews",
)

RESEARCH_PUBLISHER_PATTERNS = (
    "council on foreign relations",
    "foreign relations",
    "brookings",
    "carnegie",
    "rand",
    "chatham house",
    "international crisis group",
    "csis",
    "center for strategic and international studies",
    "bruegel",
    "ecfr",
    "cfr",
)

OFFICIAL_SOURCES = (
    {
        "title": "NATO news",
        "url": "https://www.nato.int/cps/en/natohq/news.htm",
        "publisher": "NATO",
        "source_type": "official",
        "summary": "NATO news",
    },
    {
        "title": "UN News",
        "url": "https://news.un.org/en/",
        "publisher": "United Nations",
        "source_type": "official",
        "summary": "UN News",
    },
    {
        "title": "U.S. State Department News",
        "url": "https://www.state.gov/news/",
        "publisher": "U.S. State Department",
        "source_type": "official",
        "summary": "U.S. State Department News",
    },
)

WORLD_WAR_DIRECT_PRO_TERMS = (
    "world war",
    "weltkrieg",
    "global war",
    "great power war",
    "major power war",
    "article 5",
    "nato article 5",
    "direct us-russia conflict",
    "direct u.s.-russia conflict",
    "direct us-china conflict",
    "direct u.s.-china conflict",
    "multiple major powers at war",
    "major powers at war",
    "global military conflict",
    "broader war involving major powers",
)

WORLD_WAR_DIRECT_CONTRA_TERMS = (
    "ceasefire",
    "ceasefire talks",
    "de-escalation",
    "containment",
    "restraint",
    "avoid wider war",
    "no broader war",
    "conflict remains regional",
    "diplomatic channel",
    "backchannel",
    "negotiation",
    "negotiations",
    "talks with iran",
    "held talks with iran",
    "peace talks",
    "mediation",
    "mediated talks",
    "indirect talks",
    "resume talks",
    "reopen talks",
)

WORLD_WAR_REGIONAL_ESCALATION_TERMS = (
    "regional escalation",
    "regional war",
    "broader regional war",
    "widening conflict",
    "new front",
    "open new front",
    "ground assault",
    "airstrike",
    "airstrikes",
    "missile",
    "missiles",
    "hormuz",
    "strait of hormuz",
    "red sea",
    "shipping route",
    "shipping disruption",
    "warship escorts",
    "troop buildup",
    "troop deployment",
    "houthi",
    "houthis",
    "nuclear site",
    "retaliation",
    "more strikes",
    "additional strikes",
    "fresh strikes",
)

WORLD_WAR_IRRELEVANT_CONTEXT_TERMS = (
    "lng",
    "coal-fired power",
    "coal fired power",
    "energy prices",
    "stock market",
    "earnings",
    "sports",
    "celebrity",
)

DIPLOMACY_DEDUP_TERMS = (
    "ceasefire",
    "ceasefire talks",
    "held talks with iran",
    "talks with iran",
    "diplomatic channel",
    "indirect talks",
    "reopen talks",
    "resume talks",
    "mediation",
    "de-escalation",
    "avoid wider war",
)

REGIONAL_ESCALATION_DEDUP_TERMS = (
    "hormuz",
    "red sea",
    "warship escorts",
    "ground assault",
    "new front",
    "missiles",
    "airstrikes",
    "houthi",
    "houthis",
)

MIN_RELEVANCE_BY_QUESTION_KIND = {
    "world_war": 0.14,
    "war": 0.12,
    "general": 0.08,
}


@dataclass
class ResearchSource:
    url: str
    query: str
    title: str
    domain: str
    stance: str
    weight: float
    excerpt: str
    summary: str
    publisher: str
    source_type: str
    published_at: Optional[str]
    overall_score: float
    freshness_score: float
    relevance_score: float
    signal_strength: float
    retrieval_method: str
    credibility_score: float


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_text(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _lower(text: Optional[str]) -> str:
    return _normalize_text(text).lower()


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _question_kind(question_text: str) -> str:
    q = _lower(question_text)

    if "weltkrieg" in q or "world war" in q:
        return "world_war"
    if "krieg" in q or "war" in q or "conflict" in q:
        return "war"
    return "general"


def _question_tokens(question_text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9äöüß\-]{3,}", _lower(question_text))


def _keyword_overlap(question_text: str, text: str) -> float:
    q_tokens = set(_question_tokens(question_text))
    if not q_tokens:
        return 0.25

    t_tokens = set(re.findall(r"[a-zA-Z0-9äöüß\-]{3,}", _lower(text)))
    if not t_tokens:
        return 0.0

    overlap = len(q_tokens.intersection(t_tokens))
    denom = max(4, min(len(q_tokens), 16))
    return _clamp(overlap / denom)


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _parse_google_news_title(raw_title: str) -> Tuple[str, str]:
    title = _normalize_text(raw_title)
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return title, ""


def _publisher_from_domain(domain: str) -> str:
    d = _lower(domain)
    d = d.replace("www.", "")
    return d


def _extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return (parsed.netloc or "").lower()
    except Exception:
        return ""


def _publisher_type(publisher: str, domain: str) -> str:
    publisher_text = _lower(f"{publisher} {domain}")

    if any(pattern in publisher_text for pattern in AGGREGATOR_PUBLISHER_PATTERNS):
        return "aggregator"
    if any(pattern in publisher_text for pattern in RESEARCH_PUBLISHER_PATTERNS):
        return "research"
    if any(pattern in publisher_text for pattern in WIRE_PUBLISHER_PATTERNS):
        return "wire"
    if any(pattern in publisher_text for pattern in MAJOR_MEDIA_PUBLISHER_PATTERNS):
        return "major_media"
    if domain.endswith(".gov") or domain.endswith(".int"):
        return "official"
    return "other"


def _parse_published_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _published_at_iso(value: Optional[str]) -> Optional[str]:
    dt = _parse_published_at(value)
    return dt.isoformat() if dt else None


def _freshness_score(published_at: Optional[str]) -> float:
    dt = _parse_published_at(published_at)
    if not dt:
        return 0.45

    age_days = max(0.0, (_utcnow() - dt).total_seconds() / 86400.0)
    score = math.exp(-age_days / 28.0)
    return round(_clamp(score, 0.2, 1.0), 4)


def _question_specific_relevance(question_text: str, title: str, summary: str) -> float:
    q_kind = _question_kind(question_text)
    text = _lower(f"{title}. {summary}")
    overlap = _keyword_overlap(question_text, text)

    if _contains_any(text, WORLD_WAR_IRRELEVANT_CONTEXT_TERMS):
        return 0.0

    if q_kind == "world_war":
        if _contains_any(text, WORLD_WAR_DIRECT_PRO_TERMS):
            return 0.85
        if _contains_any(text, WORLD_WAR_DIRECT_CONTRA_TERMS):
            return 0.70
        if _contains_any(text, WORLD_WAR_REGIONAL_ESCALATION_TERMS):
            return 0.18
        if "iran" in text or "israel" in text or "u.s." in text or "us " in text:
            return max(0.10, overlap * 0.45)
        return overlap * 0.25

    if q_kind == "war":
        return max(overlap * 0.75, 0.08 if "war" in text or "conflict" in text else 0.0)

    return overlap


def _classify_stance(question_text: str, title: str, summary: str) -> str:
    q_kind = _question_kind(question_text)
    text = _lower(f"{title}. {summary}")

    if q_kind == "world_war":
        if _contains_any(text, WORLD_WAR_DIRECT_PRO_TERMS):
            return "pro"
        if _contains_any(text, WORLD_WAR_DIRECT_CONTRA_TERMS):
            return "contra"
        return "uncertainty"

    if _contains_any(text, ("ceasefire", "de-escalation", "agreement", "stability")):
        return "contra"
    if _contains_any(text, ("war", "attack", "invasion", "escalation")):
        return "pro"
    return "uncertainty"


def _signal_strength(question_text: str, title: str, summary: str, source_type: str) -> float:
    text = _lower(f"{title}. {summary}")
    q_kind = _question_kind(question_text)

    if q_kind == "world_war":
        if _contains_any(text, WORLD_WAR_DIRECT_PRO_TERMS):
            return 0.78
        if _contains_any(text, WORLD_WAR_DIRECT_CONTRA_TERMS):
            return 0.62
        if _contains_any(text, WORLD_WAR_REGIONAL_ESCALATION_TERMS):
            return 0.26
        return 0.16

    base = {
        "official": 0.18,
        "wire": 0.20,
        "research": 0.18,
        "major_media": 0.16,
        "other": 0.12,
        "aggregator": 0.05,
    }.get(source_type, 0.10)
    return round(_clamp(base), 4)


def _credibility_score(source_type: str, publisher: str, domain: str) -> float:
    if source_type == "official":
        return 0.98
    if source_type == "wire":
        return 0.93
    if source_type == "research":
        return 0.82
    if source_type == "major_media":
        return 0.84
    if source_type == "aggregator":
        return 0.35

    publisher_text = _lower(f"{publisher} {domain}")
    if "cfr" in publisher_text or "council on foreign relations" in publisher_text:
        return 0.82
    return 0.60


def _overall_score(
    *,
    source_type: str,
    relevance: float,
    freshness: float,
    credibility: float,
    signal_strength: float,
) -> float:
    type_penalty = {
        "aggregator": -0.20,
        "other": 0.0,
        "major_media": 0.02,
        "research": 0.02,
        "wire": 0.05,
        "official": 0.04,
    }.get(source_type, 0.0)

    score = (
        relevance * 0.42
        + freshness * 0.16
        + credibility * 0.24
        + signal_strength * 0.18
        + type_penalty
    )
    return round(_clamp(score), 4)


def _fetch_url(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _google_news_search(query: str, *, limit: int = 10) -> List[Dict[str, Any]]:
    params = {
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    url = f"{GOOGLE_NEWS_RSS}?{urllib.parse.urlencode(params)}"

    try:
        xml_bytes = _fetch_url(url)
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []

    items: List[Dict[str, Any]] = []
    for item in root.findall(".//item")[:limit]:
        raw_title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate") or ""
        description = item.findtext("description") or ""

        title, publisher = _parse_google_news_title(raw_title)
        domain = _extract_domain(link)

        items.append(
            {
                "title": title,
                "publisher": publisher or _publisher_from_domain(domain),
                "url": link,
                "domain": domain,
                "summary": _normalize_text(description or title),
                "excerpt": "",
                "published_at": _published_at_iso(pub_date),
                "retrieval_method": "google_news_rss",
                "query": query,
            }
        )

    return items


def _query_plan(question_text: str) -> List[str]:
    q_kind = _question_kind(question_text)
    q = _normalize_text(question_text)

    if q_kind == "world_war":
        return [
            "world war risk 2026 Reuters AP AFP official",
            "diplomatic efforts avoid wider war Iran Reuters",
            "NATO UN major power conflict warning Reuters",
            "Iran talks containment wider war Reuters",
            "global war escalation risk 2026 Reuters AP",
        ]

    if q_kind == "war":
        return [
            q,
            f"{q} Reuters",
            f"{q} official statements",
        ]

    return [q, f"{q} Reuters"]


def _source_from_official_catalog(question_text: str) -> List[ResearchSource]:
    q_kind = _question_kind(question_text)
    results: List[ResearchSource] = []

    for item in OFFICIAL_SOURCES:
        relevance = 0.08 if q_kind == "world_war" else 0.10
        freshness = 0.45
        credibility = 0.98
        signal = 0.10 if q_kind == "world_war" else 0.14
        overall = _overall_score(
            source_type="official",
            relevance=relevance,
            freshness=freshness,
            credibility=credibility,
            signal_strength=signal,
        )
        results.append(
            ResearchSource(
                url=item["url"],
                query="official_catalog",
                title=item["title"],
                domain=_extract_domain(item["url"]),
                stance="neutral",
                weight=overall,
                excerpt="",
                summary=item["summary"],
                publisher=item["publisher"],
                source_type="official",
                published_at=None,
                overall_score=overall,
                freshness_score=freshness,
                relevance_score=relevance,
                signal_strength=signal,
                retrieval_method="official_catalog",
                credibility_score=credibility,
            )
        )

    return results


def _normalize_candidate(question_text: str, item: Dict[str, Any]) -> Optional[ResearchSource]:
    title = _normalize_text(item.get("title"))
    summary = _normalize_text(item.get("summary"))
    publisher = _normalize_text(item.get("publisher"))
    url = _normalize_text(item.get("url"))
    domain = _extract_domain(url)

    if not title or not url:
        return None

    source_type = _publisher_type(publisher, domain)
    if source_type == "aggregator":
        return None

    relevance = _question_specific_relevance(question_text, title, summary)
    q_kind = _question_kind(question_text)
    min_rel = MIN_RELEVANCE_BY_QUESTION_KIND.get(q_kind, 0.08)

    if relevance < min_rel:
        return None

    freshness = _freshness_score(item.get("published_at"))
    credibility = _credibility_score(source_type, publisher, domain)
    stance = _classify_stance(question_text, title, summary)
    signal = _signal_strength(question_text, title, summary, source_type)
    overall = _overall_score(
        source_type=source_type,
        relevance=relevance,
        freshness=freshness,
        credibility=credibility,
        signal_strength=signal,
    )

    return ResearchSource(
        url=url,
        query=_normalize_text(item.get("query")),
        title=title,
        domain=domain,
        stance=stance,
        weight=overall,
        excerpt=_normalize_text(item.get("excerpt")),
        summary=summary,
        publisher=publisher or _publisher_from_domain(domain),
        source_type=source_type,
        published_at=_normalize_text(item.get("published_at")) or None,
        overall_score=overall,
        freshness_score=freshness,
        relevance_score=round(relevance, 4),
        signal_strength=round(signal, 4),
        retrieval_method=_normalize_text(item.get("retrieval_method")) or "unknown",
        credibility_score=round(credibility, 4),
    )


def _dedupe_bucket_key(question_text: str, source: ResearchSource) -> str:
    text = _lower(f"{source.title}. {source.summary}")
    q_kind = _question_kind(question_text)

    if q_kind == "world_war":
        if _contains_any(text, DIPLOMACY_DEDUP_TERMS):
            return "world_war:diplomacy"
        if _contains_any(text, REGIONAL_ESCALATION_DEDUP_TERMS):
            return "world_war:regional_escalation"
        if _contains_any(text, WORLD_WAR_DIRECT_PRO_TERMS):
            return "world_war:major_power_signal"
        if source.source_type == "research":
            return "world_war:research"
    return ""


def _normalized_title_fingerprint(title: str) -> str:
    base = _lower(title)
    base = re.sub(r"[^a-z0-9äöüß\s]", " ", base)
    base = re.sub(r"\b(exclusive|analysis|live|update|tracker)\b", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _dedupe_sources(question_text: str, sources: List[ResearchSource]) -> List[ResearchSource]:
    kept: List[ResearchSource] = []
    seen_title_fp: set[str] = set()
    bucket_counts: Dict[str, int] = {}

    for source in sorted(
        sources,
        key=lambda s: (s.overall_score, s.credibility_score, s.freshness_score),
        reverse=True,
    ):
        title_fp = _normalized_title_fingerprint(source.title)
        if title_fp in seen_title_fp:
            continue

        bucket = _dedupe_bucket_key(question_text, source)
        if bucket:
            limit = 1 if bucket in {"world_war:diplomacy", "world_war:research"} else 2
            if bucket_counts.get(bucket, 0) >= limit:
                continue
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        seen_title_fp.add(title_fp)
        kept.append(source)

    return kept


def _fetch_candidates(question_text: str) -> List[ResearchSource]:
    normalized: List[ResearchSource] = []

    for query in _query_plan(question_text):
        for item in _google_news_search(query, limit=10):
            source = _normalize_candidate(question_text, item)
            if source is not None:
                normalized.append(source)

    normalized.extend(_source_from_official_catalog(question_text))
    return _dedupe_sources(question_text, normalized)


def research_sources(
    question_text: str,
    session: Any = None,
    max_sources: int = 8,
) -> List[Dict[str, Any]]:
    sources = _fetch_candidates(question_text)

    sources = sorted(
        sources,
        key=lambda s: (s.overall_score, s.relevance_score, s.credibility_score),
        reverse=True,
    )[:max_sources]

    return [asdict(source) for source in sources]
