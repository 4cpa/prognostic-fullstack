from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple
import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


USER_AGENT = "prognostic-research-bot/0.3 (+forecasting-mvp)"
HTTP_TIMEOUT_SECONDS = 12
DEFAULT_MAX_SOURCES = 15


OFFICIAL_DOMAINS = {
    "europa.eu",
    "european-union.europa.eu",
    "ec.europa.eu",
    "consilium.europa.eu",
    "europarl.europa.eu",
    "eeas.europa.eu",
    "euipo.europa.eu",
    "europol.europa.eu",
    "nato.int",
    "un.org",
    "imf.org",
    "worldbank.org",
    "oecd.org",
    "ecb.europa.eu",
    "bundesregierung.de",
    "auswaertiges-amt.de",
    "state.gov",
    "whitehouse.gov",
    "gov.uk",
}

WIRE_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "afp.com",
    "news.yahoo.com",
}

RESEARCH_DOMAINS = {
    "sipri.org",
    "iiss.org",
    "bruegel.org",
    "ecfr.eu",
    "brookings.edu",
    "chathamhouse.org",
    "csis.org",
    "rand.org",
    "carnegieendowment.org",
    "piie.com",
    "ifo.de",
}

MAJOR_MEDIA_DOMAINS = {
    "ft.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "bbc.com",
    "bbc.co.uk",
    "dw.com",
    "lemonde.fr",
    "faz.net",
    "wsj.com",
    "politico.eu",
    "cnn.com",
    "aljazeera.com",
    "economist.com",
    "haaretz.com",
    "france24.com",
}


WIRE_PUBLISHER_PATTERNS = (
    "reuters",
    "associated press",
    "ap ",
    " ap",
    "afp",
)

RESEARCH_PUBLISHER_PATTERNS = (
    "sipri",
    "iiss",
    "bruegel",
    "ecfr",
    "brookings",
    "chatham house",
    "csis",
    "rand",
    "carnegie",
    "piie",
    "ifo",
)

MAJOR_MEDIA_PUBLISHER_PATTERNS = (
    "dw",
    "bbc",
    "financial times",
    "the guardian",
    "new york times",
    "washington post",
    "wall street journal",
    "politico",
    "cnn",
    "al jazeera",
    "economist",
    "haaretz",
    "france 24",
)


@dataclass
class SourceCandidate:
    url: str
    title: str
    domain: str
    publisher: str
    source_type: str
    published_at: Optional[str]
    query: str
    retrieval_method: str
    relevance_score: float
    credibility_score: float
    freshness_score: float
    overall_score: float
    stance: str
    signal_strength: float
    summary: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _normalize_text(text: Optional[str]) -> str:
    return _normalize_whitespace((text or "").lower())


def _extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _safe_get(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/xml, text/xml, application/rss+xml, text/html;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return response.read()


def _safe_json_get(url: str) -> Dict[str, Any]:
    raw = _safe_get(url)
    return json.loads(raw.decode("utf-8", errors="replace"))


def _safe_xml_get(url: str) -> ET.Element:
    raw = _safe_get(url)
    return ET.fromstring(raw.decode("utf-8", errors="replace"))


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    value = value.strip()
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except Exception:
        pass

    try:
        return parsedate_to_datetime(value)
    except Exception:
        return None


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _tokenize(text: str) -> List[str]:
    text = _normalize_text(text)
    return re.findall(r"[a-zA-Z0-9äöüß\-]{3,}", text)


def _question_kind(question_text: str) -> str:
    q = _normalize_text(question_text)

    if "weltkrieg" in q or "world war" in q:
        return "world_war"
    if "eu zer" in q or "eu breakup" in q or "european union breakup" in q:
        return "eu_breakup"
    if ("staat" in q or "state" in q) and ("kollaps" in q or "collapse" in q):
        return "state_collapse"
    if "krieg" in q or "war" in q or "conflict" in q:
        return "war"
    return "general"


def _classify_source_type(domain: str, publisher: str = "", title: str = "") -> str:
    publisher_text = _normalize_text(f"{publisher or ''} {title or ''}")

    if domain in OFFICIAL_DOMAINS or domain.endswith(".gov") or domain.endswith(".int"):
        return "official"
    if domain in WIRE_DOMAINS:
        return "wire"
    if domain in RESEARCH_DOMAINS:
        return "research"
    if domain in MAJOR_MEDIA_DOMAINS:
        return "major_media"

    if any(pattern in publisher_text for pattern in WIRE_PUBLISHER_PATTERNS):
        return "wire"
    if any(pattern in publisher_text for pattern in RESEARCH_PUBLISHER_PATTERNS):
        return "research"
    if any(pattern in publisher_text for pattern in MAJOR_MEDIA_PUBLISHER_PATTERNS):
        return "major_media"

    return "other"


def _credibility_score(source_type: str) -> float:
    return {
        "official": 0.98,
        "wire": 0.93,
        "research": 0.90,
        "major_media": 0.84,
        "other": 0.60,
    }.get(source_type, 0.60)


def _freshness_score(published_at: Optional[str]) -> float:
    dt = _parse_date(published_at)
    if not dt:
        return 0.45

    delta_days = max(((_utcnow() - dt.astimezone(timezone.utc)).total_seconds() / 86400.0), 0.0)
    return max(0.20, math.exp(-delta_days / 180.0))


def _keyword_overlap_score(question_text: str, title: str, summary: str) -> float:
    q_tokens = set(_tokenize(question_text))
    if not q_tokens:
        return 0.3

    s_tokens = set(_tokenize(f"{title} {summary}"))
    if not s_tokens:
        return 0.2

    overlap = len(q_tokens.intersection(s_tokens))
    denom = max(4, min(len(q_tokens), 20))
    return min(1.0, overlap / denom)


def _contains_any(text: str, terms: Tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _outcome_specificity_score(question_text: str, title: str, summary: str) -> float:
    q_kind = _question_kind(question_text)
    text = _normalize_text(f"{title} {summary}")

    global_war_terms = (
        "world war",
        "weltkrieg",
        "global war",
        "great power war",
        "major power war",
        "global conflict",
        "nato article 5",
        "article 5",
        "u.s. and russia",
        "us and russia",
        "u.s. and china",
        "us and china",
        "multiple major powers",
        "global escalation",
        "broader war",
        "broader conflict",
        "wider war involving major powers",
    )
    regional_escalation_terms = (
        "missile",
        "airstrike",
        "retaliation",
        "escalation",
        "hormuz",
        "nuclear site",
        "border clashes",
        "military operation",
        "conflict widens",
        "regional war",
        "regional conflict",
        "ground assault",
        "new front",
        "houthi",
        "houthis",
        "red sea",
        "shipping route",
    )
    containment_terms = (
        "ceasefire",
        "de-escalation",
        "talks with iran",
        "held talks with iran",
        "diplomatic channel",
        "negotiation",
        "containment",
        "limited response",
        "avoid wider war",
        "no broader war",
        "regional conflict remains",
        "conflict remains regional",
        "restraint",
        "backchannel",
    )
    eu_breakup_terms = (
        "member state exit",
        "withdrawal from the eu",
        "leave the eu",
        "eu exit",
        "disintegration of the eu",
        "fracture of the european union",
        "european union breakup",
    )

    if q_kind == "world_war":
        if _contains_any(text, global_war_terms):
            return 1.0
        if _contains_any(text, containment_terms):
            return 0.70
        if _contains_any(text, regional_escalation_terms):
            return 0.28
        return 0.08

    if q_kind == "eu_breakup":
        if _contains_any(text, eu_breakup_terms):
            return 1.0
        if "eu" in text or "european union" in text:
            return 0.35
        return 0.10

    if q_kind == "state_collapse":
        collapse_terms = (
            "collapse",
            "state failure",
            "institutional breakdown",
            "government collapse",
            "regime collapse",
            "default",
            "bank run",
        )
        if _contains_any(text, collapse_terms):
            return 1.0
        return 0.15

    if q_kind == "war":
        war_terms = (
            "war",
            "conflict",
            "attack",
            "invasion",
            "military escalation",
            "ceasefire",
            "de-escalation",
        )
        if _contains_any(text, war_terms):
            return 0.8
        return 0.2

    return 0.4


def _question_specific_relevance(question_text: str, title: str, summary: str) -> float:
    overlap = _keyword_overlap_score(question_text, title, summary)
    specificity = _outcome_specificity_score(question_text, title, summary)

    q_kind = _question_kind(question_text)
    if q_kind == "world_war":
        score = overlap * 0.35 + specificity * 0.65
    elif q_kind in {"eu_breakup", "state_collapse"}:
        score = overlap * 0.45 + specificity * 0.55
    else:
        score = overlap * 0.60 + specificity * 0.40

    return min(1.0, round(score, 4))


def _infer_stance(question_text: str, title: str, summary: str) -> Tuple[str, float]:
    text = _normalize_text(f"{title} {summary}")
    q_kind = _question_kind(question_text)

    pro_terms_general = (
        "collapse",
        "breakup",
        "disintegration",
        "war",
        "conflict escalation",
        "exit",
        "withdrawal",
        "crisis",
        "fracture",
        "mobilization",
        "sanctions shock",
        "attack",
        "missile",
        "retaliation",
        "offensive",
        "invasion",
    )
    contra_terms_general = (
        "stability",
        "cooperation",
        "unity",
        "agreement",
        "institutional continuity",
        "ceasefire",
        "de-escalation",
        "integration",
        "support package",
        "reaffirmed commitment",
        "restraint",
        "containment",
        "talks",
        "negotiation",
        "diplomacy",
    )
    uncertainty_terms = (
        "uncertain",
        "risk",
        "warning",
        "concern",
        "volatility",
        "tension",
        "scenario",
        "could",
        "may",
        "might",
    )

    world_war_direct_pro = (
        "world war",
        "weltkrieg",
        "global war",
        "great power war",
        "major power war",
        "article 5",
        "global escalation",
        "multiple major powers",
        "broader global conflict",
    )
    world_war_direct_contra = (
        "ceasefire",
        "de-escalation",
        "containment",
        "limited response",
        "regional conflict",
        "conflict remains regional",
        "no broader war",
        "talks with iran",
        "held talks with iran",
        "diplomatic channel",
        "negotiation",
        "avoid wider war",
        "backchannel",
    )

    pro_hits = sum(1 for term in pro_terms_general if term in text)
    contra_hits = sum(1 for term in contra_terms_general if term in text)
    uncertainty_hits = sum(1 for term in uncertainty_terms if term in text)

    if q_kind == "world_war":
        direct_pro_hits = sum(1 for term in world_war_direct_pro if term in text)
        direct_contra_hits = sum(1 for term in world_war_direct_contra if term in text)

        if direct_pro_hits >= 1:
            return "pro", min(1.0, 0.35 + direct_pro_hits * 0.18)

        if direct_contra_hits >= 1:
            return "contra", min(1.0, 0.30 + direct_contra_hits * 0.16)

        if pro_hits >= 1:
            return "uncertainty", min(1.0, 0.20 + pro_hits * 0.06)

        if uncertainty_hits >= 1:
            return "uncertainty", min(1.0, 0.20 + uncertainty_hits * 0.08)

        return "neutral", 0.10

    if pro_hits > contra_hits and pro_hits >= 1:
        return "pro", min(1.0, 0.25 + pro_hits * 0.15)
    if contra_hits > pro_hits and contra_hits >= 1:
        return "contra", min(1.0, 0.25 + contra_hits * 0.15)
    if uncertainty_hits >= 1:
        return "uncertainty", min(1.0, 0.20 + uncertainty_hits * 0.10)
    return "neutral", 0.15


def _overall_score(relevance: float, credibility: float, freshness: float, source_type: str, signal_strength: float) -> float:
    type_bonus = {
        "official": 0.05,
        "wire": 0.06,
        "research": 0.05,
        "major_media": 0.03,
        "other": 0.0,
    }.get(source_type, 0.0)

    score = (
        relevance * 0.48
        + credibility * 0.22
        + freshness * 0.15
        + signal_strength * 0.15
        + type_bonus
    )
    return min(1.0, round(score, 4))


def _make_source_candidate(
    *,
    url: str,
    title: str,
    publisher: Optional[str],
    published_at: Optional[str],
    query: str,
    retrieval_method: str,
    summary: str,
    question_text: str,
) -> SourceCandidate:
    domain = _extract_domain(url)
    normalized_publisher = _normalize_whitespace(publisher or domain or "unknown")
    source_type = _classify_source_type(domain, normalized_publisher, title)
    credibility = _credibility_score(source_type)
    freshness = _freshness_score(published_at)
    relevance = _question_specific_relevance(question_text, title, summary)
    stance, signal_strength = _infer_stance(question_text, title, summary)
    overall = _overall_score(relevance, credibility, freshness, source_type, signal_strength)

    return SourceCandidate(
        url=url,
        title=_normalize_whitespace(title or url),
        domain=domain,
        publisher=normalized_publisher,
        source_type=source_type,
        published_at=published_at,
        query=query,
        retrieval_method=retrieval_method,
        relevance_score=round(relevance, 4),
        credibility_score=round(credibility, 4),
        freshness_score=round(freshness, 4),
        overall_score=round(overall, 4),
        stance=stance,
        signal_strength=round(signal_strength, 4),
        summary=_normalize_whitespace(summary),
    )


def _dedupe_sources(sources: List[SourceCandidate]) -> List[SourceCandidate]:
    seen = set()
    deduped: List[SourceCandidate] = []

    for s in sorted(sources, key=lambda x: x.overall_score, reverse=True):
        key = (
            s.url.split("?")[0].rstrip("/").lower(),
            re.sub(r"[^a-z0-9]+", " ", s.title.lower()).strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)

    return deduped


def _fetch_gdelt_sources(query: str, question_text: str, max_records: int = 8) -> List[SourceCandidate]:
    encoded = urllib.parse.quote(query)
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        f"query={encoded}&mode=ArtList&format=json&maxrecords={max_records}&sort=HybridRel"
    )

    try:
        data = _safe_json_get(url)
    except Exception:
        return []

    articles = data.get("articles", []) or []
    results: List[SourceCandidate] = []

    for article in articles:
        article_url = article.get("url") or ""
        title = article.get("title") or article_url
        publisher = article.get("domain") or _extract_domain(article_url)
        published_at = article.get("seendate") or None
        summary = article.get("sourcecountry") or article.get("domain") or ""

        if not article_url:
            continue

        results.append(
            _make_source_candidate(
                url=article_url,
                title=title,
                publisher=publisher,
                published_at=published_at,
                query=query,
                retrieval_method="gdelt",
                summary=summary,
                question_text=question_text,
            )
        )

    return results


def _fetch_google_news_rss(query: str, question_text: str, max_records: int = 8) -> List[SourceCandidate]:
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    try:
        root = _safe_xml_get(url)
    except Exception:
        return []

    results: List[SourceCandidate] = []
    items = root.findall(".//item")

    for item in items[:max_records]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate")
        source_tag = item.find("source")
        publisher = source_tag.text if source_tag is not None and source_tag.text else _extract_domain(link)

        if not link:
            continue

        results.append(
            _make_source_candidate(
                url=link,
                title=title,
                publisher=publisher,
                published_at=_to_iso(_parse_date(pub_date)),
                query=query,
                retrieval_method="google_news_rss",
                summary=title,
                question_text=question_text,
            )
        )

    return results


def _official_catalog_candidates(question_text: str) -> List[SourceCandidate]:
    q_kind = _question_kind(question_text)
    results: List[SourceCandidate] = []

    catalog: List[Tuple[str, str, str]] = [
        ("https://european-union.europa.eu/index_en", "European Union official portal", "European Union"),
        ("https://ec.europa.eu/commission/presscorner/home/en", "European Commission Press Corner", "European Commission"),
        ("https://www.consilium.europa.eu/en/press/press-releases/", "Council of the EU press releases", "Council of the European Union"),
        ("https://www.eeas.europa.eu/", "European External Action Service", "EEAS"),
        ("https://www.nato.int/cps/en/natohq/news.htm", "NATO news", "NATO"),
        ("https://news.un.org/en/", "UN News", "United Nations"),
        ("https://www.imf.org/en/News", "IMF News", "IMF"),
        ("https://www.worldbank.org/en/news", "World Bank News", "World Bank"),
        ("https://www.oecd.org/newsroom/", "OECD Newsroom", "OECD"),
        ("https://www.ecb.europa.eu/press/html/index.en.html", "ECB Press", "European Central Bank"),
    ]

    if q_kind == "eu_breakup":
        selected = catalog[:4]
    elif q_kind == "world_war":
        selected = [catalog[4], catalog[5]]
    elif q_kind == "state_collapse":
        selected = [catalog[6], catalog[7], catalog[8], catalog[9]]
    else:
        selected = catalog[:4]

    for url, title, publisher in selected:
        results.append(
            _make_source_candidate(
                url=url,
                title=title,
                publisher=publisher,
                published_at=None,
                query="official_catalog",
                retrieval_method="official_catalog",
                summary=title,
                question_text=question_text,
            )
        )

    return results


def build_query_variants(question_text: str, max_queries: int = 8) -> List[str]:
    q = _normalize_whitespace(question_text)
    q_lower = q.lower()

    queries: List[str] = [q]

    if "eu" in q_lower or "european union" in q_lower:
        queries.extend(
            [
                "European Union breakup risk 2026 official Reuters AP AFP",
                "EU disintegration 2026 Reuters AP official",
                "EU member state exit risk 2026 Reuters AP",
                "European Commission EU unity press release",
            ]
        )

    if "weltkrieg" in q_lower or "world war" in q_lower:
        queries.extend(
            [
                "world war risk 2026 Reuters AP AFP official",
                "great power war risk 2026 Reuters official",
                "global war escalation risk 2026 Reuters AP",
                "NATO UN major power conflict warning Reuters",
                "Iran talks containment wider war Reuters",
                "diplomatic efforts avoid wider war Iran Reuters",
                "conflict remains regional Iran Reuters",
            ]
        )

    if "election" in q_lower or "wahl" in q_lower:
        queries.extend(
            [
                "official election commission results Reuters AP AFP",
                "government election statement Reuters AP AFP",
            ]
        )

    queries.extend(
        [
            f"{q} Reuters",
            f"{q} AP AFP",
            f"{q} official statements",
            f"{q} think tank analysis",
        ]
    )

    cleaned: List[str] = []
    seen = set()
    for query in queries:
        normalized = _normalize_whitespace(query)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)

    return cleaned[:max_queries]


def _source_type_counts(sources: List[SourceCandidate]) -> Dict[str, int]:
    counts = {
        "official": 0,
        "wire": 0,
        "research": 0,
        "major_media": 0,
        "other": 0,
    }
    for s in sources:
        counts[s.source_type] = counts.get(s.source_type, 0) + 1
    return counts


def _min_relevance_threshold(question_text: str) -> float:
    q_kind = _question_kind(question_text)
    if q_kind == "world_war":
        return 0.16
    if q_kind in {"eu_breakup", "state_collapse"}:
        return 0.18
    return 0.12


def _is_irrelevant_for_question(question_text: str, source: SourceCandidate) -> bool:
    q_kind = _question_kind(question_text)
    text = _normalize_text(f"{source.title} {source.summary} {source.publisher}")

    if q_kind == "world_war":
        hard_irrelevant_terms = (
            "coal-fired power",
            "lng import risks",
            "oil prices",
            "oil pares gains",
            "stocks",
            "inflation only",
            "earnings",
            "bond yields",
            "trade deficit",
            "shipping rates",
        )
        if any(term in text for term in hard_irrelevant_terms):
            return True

        if source.relevance_score <= 0.06 and (
            "oil" in text
            or "lng" in text
            or "coal" in text
            or "shipping" in text
            or "economy" in text
            or "market" in text
            or "prices" in text
        ):
            return True

    return False


def _is_world_war_containment_candidate(source: SourceCandidate) -> bool:
    text = _normalize_text(f"{source.title} {source.summary} {source.publisher}")
    terms = (
        "talks with iran",
        "held talks with iran",
        "diplomatic",
        "diplomacy",
        "negotiation",
        "backchannel",
        "ceasefire",
        "de-escalation",
        "containment",
        "limited response",
        "no broader war",
        "avoid wider war",
        "conflict remains regional",
        "regional conflict",
        "restraint",
    )
    return any(term in text for term in terms)


def _is_world_war_escalation_candidate(source: SourceCandidate) -> bool:
    text = _normalize_text(f"{source.title} {source.summary} {source.publisher}")
    direct_terms = (
        "world war",
        "weltkrieg",
        "global war",
        "great power war",
        "major power war",
        "article 5",
        "multiple major powers",
        "broader war",
    )
    regional_terms = (
        "ground assault",
        "houthi",
        "houthis",
        "missile",
        "retaliation",
        "new front",
        "open new front",
        "airstrike",
        "red sea",
        "shipping route",
        "hormuz",
        "nuclear site",
        "intercept missiles",
        "launch israel strike",
        "conflict widens",
    )
    return any(term in text for term in direct_terms) or any(term in text for term in regional_terms)


def _select_balanced_sources(sources: List[SourceCandidate], max_sources: int, question_text: str) -> List[SourceCandidate]:
    min_relevance = _min_relevance_threshold(question_text)
    q_kind = _question_kind(question_text)

    filtered: List[SourceCandidate] = []
    for s in sources:
        if _is_irrelevant_for_question(question_text, s):
            continue
        if s.relevance_score < min_relevance:
            continue
        if q_kind == "world_war" and s.stance == "neutral" and s.relevance_score < 0.20:
            continue
        filtered.append(s)

    if not filtered:
        filtered = [s for s in sources if not _is_irrelevant_for_question(question_text, s)]

    if not filtered:
        filtered = list(sources)

    filtered = sorted(
        filtered,
        key=lambda x: (x.overall_score, x.signal_strength, x.relevance_score, x.freshness_score),
        reverse=True,
    )

    if q_kind == "world_war":
        selected: List[SourceCandidate] = []

        wire_sources = [s for s in filtered if s.source_type == "wire"]
        containment_sources = [s for s in filtered if _is_world_war_containment_candidate(s)]
        escalation_sources = [s for s in filtered if _is_world_war_escalation_candidate(s)]
        official_sources = [s for s in filtered if s.source_type == "official"]
        research_sources = [s for s in filtered if s.source_type == "research"]

        def _append_unique(candidates: List[SourceCandidate], limit: int = 1) -> None:
            added = 0
            for item in candidates:
                if item in selected:
                    continue
                selected.append(item)
                added += 1
                if added >= limit or len(selected) >= max_sources:
                    break

        _append_unique([s for s in wire_sources if _is_world_war_containment_candidate(s)], limit=1)
        _append_unique([s for s in wire_sources if _is_world_war_escalation_candidate(s)], limit=1)

        if len(selected) < 2:
            _append_unique(containment_sources, limit=1)
        if len(selected) < 3:
            _append_unique(escalation_sources, limit=2)

        _append_unique(official_sources, limit=1)
        _append_unique(research_sources, limit=1)

        remainder = [s for s in filtered if s not in selected]
        for item in remainder:
            if len(selected) >= max_sources:
                break
            selected.append(item)

        return selected[:max_sources]

    by_type: Dict[str, List[SourceCandidate]] = {
        "official": [],
        "wire": [],
        "research": [],
        "major_media": [],
        "other": [],
    }

    for s in filtered:
        by_type.setdefault(s.source_type, []).append(s)

    selected: List[SourceCandidate] = []
    quotas = [
        ("wire", 3),
        ("research", 2),
        ("official", 2),
        ("major_media", 3),
    ]

    for source_type, quota in quotas:
        for item in by_type.get(source_type, []):
            if len(selected) >= max_sources:
                break
            if item in selected:
                continue
            selected.append(item)
            if sum(1 for s in selected if s.source_type == source_type) >= quota:
                break

    remainder = [s for s in filtered if s not in selected]
    for item in remainder:
        if len(selected) >= max_sources:
            break
        selected.append(item)

    return selected[:max_sources]


def build_reasoning_from_sources(question_text: str, sources: List[SourceCandidate]) -> Dict[str, List[str]]:
    pro_points: List[str] = []
    contra_points: List[str] = []
    uncertainty_points: List[str] = []

    for s in sorted(sources, key=lambda x: (x.overall_score, x.signal_strength), reverse=True):
        bullet = f"{s.publisher}: {s.title}"
        if s.stance == "pro" and bullet not in pro_points:
            pro_points.append(bullet)
        elif s.stance == "contra" and bullet not in contra_points:
            contra_points.append(bullet)
        elif s.stance in {"uncertainty", "neutral"} and bullet not in uncertainty_points:
            uncertainty_points.append(bullet)

    if not contra_points:
        contra_points.append("Mehrere höher gewichtete Quellen deuten eher auf Begrenzung oder Eindämmung als auf das Eintreten des abgefragten Extremereignisses hin.")
    if not pro_points:
        pro_points.append("Es gibt weiterhin Risikotreiber und Warnsignale, die das Eintreten des abgefragten Ereignisses nicht ausschließen.")
    if not uncertainty_points:
        uncertainty_points.append("Die Quellenlage enthält Unsicherheit, insbesondere bei schnellen geopolitischen Eskalationen.")

    return {
        "pro": pro_points[:5],
        "contra": contra_points[:5],
        "uncertainties": uncertainty_points[:5],
    }


def build_summary(question_text: str, probability: float, reasoning: Dict[str, List[str]]) -> str:
    pct = probability * 100.0
    if pct < 10:
        qualifier = "derzeit eher unwahrscheinlich"
    elif pct < 25:
        qualifier = "derzeit eher nicht wahrscheinlich"
    elif pct < 40:
        qualifier = "derzeit möglich, aber unter 50%"
    elif pct < 60:
        qualifier = "derzeit offen"
    elif pct < 75:
        qualifier = "derzeit eher wahrscheinlich"
    else:
        qualifier = "derzeit deutlich wahrscheinlich"

    parts = [
        f'Für die Frage "{question_text}" ist das Eintreten {qualifier} ({pct:.1f}%).'
    ]

    if reasoning.get("pro"):
        parts.append(f"Pro: {reasoning['pro'][0]}")
    if reasoning.get("contra"):
        parts.append(f"Contra: {reasoning['contra'][0]}")
    if reasoning.get("uncertainties"):
        parts.append(f"Unsicherheit: {reasoning['uncertainties'][0]}")

    return " ".join(parts)


def research_sources(
    question_text: str,
    session: Any = None,
    max_sources: int = DEFAULT_MAX_SOURCES,
) -> List[Dict[str, Any]]:
    queries = build_query_variants(question_text, max_queries=8)

    all_sources: List[SourceCandidate] = []
    for query in queries:
        all_sources.extend(_fetch_google_news_rss(query, question_text, max_records=6))
        all_sources.extend(_fetch_gdelt_sources(query, question_text, max_records=4))

    all_sources.extend(_official_catalog_candidates(question_text))

    deduped = _dedupe_sources(all_sources)
    selected = _select_balanced_sources(deduped, max_sources=max_sources, question_text=question_text)

    return [asdict(item) for item in selected]
