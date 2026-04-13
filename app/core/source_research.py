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


# ---------------------------------------------------------------------------
# Publisher-Klassifizierung
# ---------------------------------------------------------------------------

WIRE_PUBLISHER_PATTERNS = ("reuters", "associated press", "ap ", "apnews", "afp", "bloomberg")
MAJOR_MEDIA_PUBLISHER_PATTERNS = (
    "dw", "dw.com", "bbc", "cnn", "france 24", "al jazeera", "the guardian",
    "financial times", "wsj", "wall street journal", "new york times",
    "washington post", "economist", "cnbc", "haaretz",
)
AGGREGATOR_PUBLISHER_PATTERNS = ("msn", "yahoo", "aol", "newsbreak", "flipboard", "smartnews")
RESEARCH_PUBLISHER_PATTERNS = (
    "council on foreign relations", "brookings", "carnegie", "rand", "chatham house",
    "international crisis group", "csis", "bruegel", "ecfr", "cfr",
)

# ---------------------------------------------------------------------------
# Themen-Erkennung
# ---------------------------------------------------------------------------

_KIND_PATTERNS: List[Tuple[str, Tuple[str, ...]]] = [
    ("world_war", ("weltkrieg", "world war", "dritter weltkrieg", "third world war")),
    ("war", ("krieg", " war ", "conflict", "military", "troops", "invasion", "nato", "ukraine", "gaza", "israel")),
    ("economics", (
        "stock", "aktie", "price", "preis", "market", "börse", "crypto", "bitcoin",
        "inflation", "recession", "gdp", "interest rate", "zinsen", "economy",
        "wirtschaft", "dax", "nasdaq", "s&p", "dollar", "euro", "currency",
    )),
    ("politics", (
        "election", "wahl", "president", "präsident", "chancellor", "kanzler",
        "parliament", "congress", "senate", "minister", "government", "regierung",
        "referendum", "abstimmung", "vote", "partei", "party",
    )),
    ("technology", (
        "ai", "artificial intelligence", "software", "app", "tech", "startup",
        "apple", "google", "microsoft", "meta", "openai", "chip", "semiconductor",
        "smartphone", "electric vehicle", "ev", "tesla",
    )),
    ("health", (
        "vaccine", "impfstoff", "pandemic", "pandemie", "virus", "disease",
        "krankheit", "cancer", "drug", "medikament", "fda", "who", "health",
        "gesundheit", "clinical trial", "studie",
    )),
    ("sports", (
        "cup", "championship", "meisterschaft", "league", "tournament",
        "fifa", "uefa", "olympic", "olympia", "nfl", "nba", "bundesliga",
        "football", "soccer", "tennis", "formula 1", "f1",
    )),
    ("climate", (
        "climate", "klima", "temperature", "emission", "co2", "fossil", "renewable",
        "solar", "wind energy", "glacier", "sea level", "carbon",
    )),
]


def _question_kind(question_text: str) -> str:
    q = re.sub(r"\s+", " ", (question_text or "").strip()).lower()
    for kind, patterns in _KIND_PATTERNS:
        if any(p in q for p in patterns):
            return kind
    return "general"


def _is_geopolitical(kind: str) -> bool:
    return kind in {"world_war", "war"}


# ---------------------------------------------------------------------------
# Stance-Signale pro Thema
# ---------------------------------------------------------------------------

# Generische Signale: (positive_terms, negative_terms)
_GENERIC_PRO_TERMS = (
    "confirms", "confirmed", "achieves", "achieved", "reaches", "reached",
    "launches", "launched", "announces", "announced", "advances", "approved",
    "succeeds", "wins", "gains", "rises", "surges", "grows", "expands",
    "breaks record", "new high", "record high", "record",
)
_GENERIC_CONTRA_TERMS = (
    "fails", "failed", "cancels", "cancelled", "delays", "delayed",
    "rejects", "rejected", "misses", "missed", "crashes", "loses", "lost",
    "falls", "drops", "declines", "collapses", "bankruptcy", "bankrupt",
    "blocks", "blocked", "postponed", "retreat", "disappoints",
)

_STANCE_SIGNALS: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    "economics": (
        ("rise", "surge", "rally", "gain", "growth", "profit", "record", "outperform", "bull", "up"),
        ("fall", "crash", "decline", "loss", "recession", "deficit", "bear", "down", "miss", "default"),
    ),
    "politics": (
        ("wins", "elected", "passes", "approved", "majority", "victory", "advances", "signs"),
        ("loses", "defeated", "fails", "rejected", "blocked", "vetoed", "scandal", "resigns"),
    ),
    "technology": (
        ("launches", "releases", "breakthrough", "approved", "acquired", "partnership", "record"),
        ("fails", "delays", "banned", "fined", "recall", "layoffs", "cancelled", "drops"),
    ),
    "health": (
        ("approved", "effective", "successful", "breakthrough", "cures", "reduces", "prevents"),
        ("fails", "rejected", "side effects", "withdrawn", "ineffective", "outbreak", "spread"),
    ),
    "sports": (
        ("wins", "advances", "champions", "scores", "victory", "gold", "qualifies", "beats"),
        ("loses", "eliminated", "defeated", "injured", "suspended", "disqualified"),
    ),
    "climate": (
        ("reduces", "below", "targets", "renewable", "agreement", "milestone", "record low"),
        ("exceeds", "record high", "fails", "retreat", "melts", "rises", "floods", "drought"),
    ),
    "world_war": (
        ("world war", "weltkrieg", "global war", "article 5", "major power", "direct conflict"),
        ("ceasefire", "de-escalation", "diplomacy", "negotiations", "peace", "containment"),
    ),
    "war": (
        ("offensive", "invasion", "attack", "airstrikes", "casualties", "escalation"),
        ("ceasefire", "peace talks", "withdrawal", "agreement", "truce", "mediation"),
    ),
}

MIN_RELEVANCE_BY_KIND: Dict[str, float] = {
    "world_war": 0.14,
    "war": 0.10,
    "economics": 0.06,
    "politics": 0.06,
    "technology": 0.06,
    "health": 0.06,
    "sports": 0.06,
    "climate": 0.06,
    "general": 0.05,
}

# Offizielle Quellen nur für geopolitische Fragen
GEOPOLITICAL_OFFICIAL_SOURCES = (
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


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

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
    return _lower(domain).replace("www.", "")


def _extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return (parsed.netloc or "").lower()
    except Exception:
        return ""


def _publisher_type(publisher: str, domain: str) -> str:
    publisher_text = _lower(f"{publisher} {domain}")
    if any(p in publisher_text for p in AGGREGATOR_PUBLISHER_PATTERNS):
        return "aggregator"
    if any(p in publisher_text for p in RESEARCH_PUBLISHER_PATTERNS):
        return "research"
    if any(p in publisher_text for p in WIRE_PUBLISHER_PATTERNS):
        return "wire"
    if any(p in publisher_text for p in MAJOR_MEDIA_PUBLISHER_PATTERNS):
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


# ---------------------------------------------------------------------------
# Relevanz, Stance, Signal — themenunabhängig
# ---------------------------------------------------------------------------

def _question_specific_relevance(question_text: str, title: str, summary: str) -> float:
    kind = _question_kind(question_text)
    text = _lower(f"{title}. {summary}")
    overlap = _keyword_overlap(question_text, text)

    # Geopolitisch: spezialisierte Logik
    if kind == "world_war":
        pro_terms, contra_terms = _STANCE_SIGNALS["world_war"]
        if _contains_any(text, pro_terms):
            return 0.85
        if _contains_any(text, contra_terms):
            return 0.70
        if any(w in text for w in ("iran", "israel", "u.s.", "russia", "china", "nato")):
            return max(0.10, overlap * 0.45)
        return overlap * 0.25

    if kind == "war":
        return max(overlap * 0.75, 0.10 if _contains_any(text, ("war", "conflict", "military")) else 0.0)

    # Alle anderen Themen: Keyword-Overlap, leicht geboosted wenn Signalbegriffe passen
    if kind in _STANCE_SIGNALS:
        pro_terms, contra_terms = _STANCE_SIGNALS[kind]
        if _contains_any(text, pro_terms) or _contains_any(text, contra_terms):
            return _clamp(overlap + 0.15)

    return overlap


def _classify_stance(question_text: str, title: str, summary: str) -> str:
    kind = _question_kind(question_text)
    text = _lower(f"{title}. {summary}")

    if kind in _STANCE_SIGNALS:
        pro_terms, contra_terms = _STANCE_SIGNALS[kind]
        has_pro = _contains_any(text, pro_terms)
        has_contra = _contains_any(text, contra_terms)
        if has_pro and not has_contra:
            return "pro"
        if has_contra and not has_pro:
            return "contra"

    # Generische Fallback-Signale
    if _contains_any(text, _GENERIC_PRO_TERMS):
        return "pro"
    if _contains_any(text, _GENERIC_CONTRA_TERMS):
        return "contra"

    return "uncertainty"


def _signal_strength(question_text: str, title: str, summary: str, source_type: str) -> float:
    kind = _question_kind(question_text)
    text = _lower(f"{title}. {summary}")

    if kind in _STANCE_SIGNALS:
        pro_terms, contra_terms = _STANCE_SIGNALS[kind]
        if kind == "world_war":
            if _contains_any(text, pro_terms):
                return 0.78
            if _contains_any(text, contra_terms):
                return 0.62
            return 0.16
        has_signal = _contains_any(text, pro_terms) or _contains_any(text, contra_terms)
        if has_signal:
            base = {"wire": 0.55, "research": 0.50, "major_media": 0.45, "official": 0.52}.get(source_type, 0.38)
            return round(_clamp(base), 4)

    # Quellentyp-Basis
    base = {
        "official": 0.28,
        "wire": 0.30,
        "research": 0.28,
        "major_media": 0.24,
        "other": 0.18,
        "aggregator": 0.05,
    }.get(source_type, 0.15)
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


# ---------------------------------------------------------------------------
# Query-Plan: LLM-basiert mit Fallback
# ---------------------------------------------------------------------------

def _query_plan_fallback(question_text: str) -> List[str]:
    """Regelbasierter Fallback falls kein LLM verfügbar."""
    kind = _question_kind(question_text)
    q = _normalize_text(question_text)

    if kind == "world_war":
        return [
            "world war risk 2026 Reuters AP AFP official",
            "diplomatic efforts avoid wider war Reuters",
            "NATO UN major power conflict warning",
            "global war escalation risk Reuters AP",
        ]
    if kind == "war":
        return [q, f"{q} Reuters", f"{q} ceasefire diplomacy"]
    if kind == "economics":
        return [q, f"{q} Reuters", f"{q} analyst forecast"]
    if kind == "politics":
        return [q, f"{q} election results", f"{q} Reuters"]
    if kind == "technology":
        return [q, f"{q} announcement", f"{q} Reuters"]
    if kind == "health":
        return [q, f"{q} study results", f"{q} WHO FDA"]
    if kind == "sports":
        return [q, f"{q} match results", f"{q} championship"]

    return [q, f"{q} Reuters"]


def _query_plan(question_text: str) -> List[str]:
    """Generiert Suchanfragen via Gemini, Fallback auf Regellogik."""
    try:
        from app.core.llm_service import generate_search_queries
        queries = generate_search_queries(question_text)
        if queries:
            return queries
    except Exception:
        pass
    return _query_plan_fallback(question_text)


# ---------------------------------------------------------------------------
# Google News Fetch
# ---------------------------------------------------------------------------

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
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
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

        items.append({
            "title": title,
            "publisher": publisher or _publisher_from_domain(domain),
            "url": link,
            "domain": domain,
            "summary": _normalize_text(description or title),
            "excerpt": "",
            "published_at": _published_at_iso(pub_date),
            "retrieval_method": "google_news_rss",
            "query": query,
        })

    return items


# ---------------------------------------------------------------------------
# Kandidaten normalisieren & deduplizieren
# ---------------------------------------------------------------------------

def _source_from_official_catalog(question_text: str) -> List[ResearchSource]:
    """Offizielle Quellen nur für geopolitische Fragen einbinden."""
    kind = _question_kind(question_text)
    if not _is_geopolitical(kind):
        return []

    results: List[ResearchSource] = []
    for item in GEOPOLITICAL_OFFICIAL_SOURCES:
        relevance = 0.08 if kind == "world_war" else 0.10
        freshness = 0.45
        credibility = 0.98
        signal = 0.10
        overall = _overall_score(
            source_type="official",
            relevance=relevance,
            freshness=freshness,
            credibility=credibility,
            signal_strength=signal,
        )
        results.append(ResearchSource(
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
        ))
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
    kind = _question_kind(question_text)
    min_rel = MIN_RELEVANCE_BY_KIND.get(kind, 0.05)

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


def _normalized_title_fingerprint(title: str) -> str:
    base = _lower(title)
    base = re.sub(r"[^a-z0-9äöüß\s]", " ", base)
    base = re.sub(r"\b(exclusive|analysis|live|update|tracker)\b", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _dedupe_sources(sources: List[ResearchSource]) -> List[ResearchSource]:
    kept: List[ResearchSource] = []
    seen_title_fp: set[str] = set()

    for source in sorted(
        sources,
        key=lambda s: (s.overall_score, s.credibility_score, s.freshness_score),
        reverse=True,
    ):
        title_fp = _normalized_title_fingerprint(source.title)
        if title_fp in seen_title_fp:
            continue
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
    return _dedupe_sources(normalized)


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def research_sources(
    question_text: str,
    session: Any = None,
    max_sources: int = 4,
) -> List[Dict[str, Any]]:
    sources = _fetch_candidates(question_text)

    sources = sorted(
        sources,
        key=lambda s: (s.overall_score, s.relevance_score, s.credibility_score),
        reverse=True,
    )[:max_sources]

    return [asdict(source) for source in sources]
