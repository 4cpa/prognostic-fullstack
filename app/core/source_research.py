import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple


USER_AGENT = "prognostic-research-bot/0.1 (+forecasting-mvp)"
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
    "news.yahoo.com",  # oft Reuters/AP-Republishes
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
}


@dataclass
class SourceCandidate:
    url: str
    title: str
    domain: str
    publisher: str
    source_type: str  # official | wire | research | major_media | other
    published_at: Optional[str]
    query: str
    retrieval_method: str  # gdelt | google_news_rss | official_catalog
    relevance_score: float
    credibility_score: float
    freshness_score: float
    overall_score: float
    stance: str  # pro | contra | neutral | uncertainty
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


def _classify_source_type(domain: str) -> str:
    if domain in OFFICIAL_DOMAINS or domain.endswith(".gov") or domain.endswith(".int"):
        return "official"
    if domain in WIRE_DOMAINS:
        return "wire"
    if domain in RESEARCH_DOMAINS:
        return "research"
    if domain in MAJOR_MEDIA_DOMAINS:
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
    # langsamer Abfall; neue Quellen werden bevorzugt
    return max(0.20, math.exp(-delta_days / 180.0))


def _tokenize(text: str) -> List[str]:
    text = _normalize_text(text)
    return re.findall(r"[a-zA-Z0-9äöüß\-]{3,}", text)


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


def _infer_stance(question_text: str, title: str, summary: str) -> Tuple[str, float]:
    text = _normalize_text(f"{title} {summary}")
    q = _normalize_text(question_text)

    pro_terms = [
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
    ]
    contra_terms = [
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
    ]
    uncertainty_terms = [
        "uncertain",
        "risk",
        "warning",
        "concern",
        "volatility",
        "tension",
        "scenario",
        "could",
        "may",
    ]

    pro_hits = sum(1 for t in pro_terms if t in text)
    contra_hits = sum(1 for t in contra_terms if t in text)
    uncertainty_hits = sum(1 for t in uncertainty_terms if t in text)

    # kleine thematische Spezialfälle
    if ("weltkrieg" in q or "world war" in q) and ("ceasefire" in text or "de-escalation" in text):
        contra_hits += 1
    if ("eu" in q or "european union" in q) and ("unity" in text or "agreement" in text):
        contra_hits += 1
    if ("eu" in q or "european union" in q) and ("exit" in text or "withdrawal" in text or "fracture" in text):
        pro_hits += 1

    if pro_hits > contra_hits and pro_hits >= 1:
        return "pro", min(1.0, 0.25 + pro_hits * 0.15)
    if contra_hits > pro_hits and contra_hits >= 1:
        return "contra", min(1.0, 0.25 + contra_hits * 0.15)
    if uncertainty_hits >= 1:
        return "uncertainty", min(1.0, 0.20 + uncertainty_hits * 0.10)
    return "neutral", 0.15


def _overall_score(relevance: float, credibility: float, freshness: float, source_type: str) -> float:
    type_bonus = {
        "official": 0.08,
        "wire": 0.06,
        "research": 0.05,
        "major_media": 0.03,
        "other": 0.0,
    }.get(source_type, 0.0)

    score = (relevance * 0.50) + (credibility * 0.30) + (freshness * 0.20) + type_bonus
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
    source_type = _classify_source_type(domain)
    credibility = _credibility_score(source_type)
    freshness = _freshness_score(published_at)
    relevance = _keyword_overlap_score(question_text, title, summary)
    stance, signal_strength = _infer_stance(question_text, title, summary)
    overall = _overall_score(relevance, credibility, freshness, source_type)

    return SourceCandidate(
        url=url,
        title=_normalize_whitespace(title or url),
        domain=domain,
        publisher=_normalize_whitespace(publisher or domain or "unknown"),
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
        published_at = article.get("seendate") or article.get("socialimage") or None
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
    q = _normalize_text(question_text)
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

    if "eu" in q or "european union" in q:
        selected = catalog[:4] + catalog[7:10]
    elif "world war" in q or "weltkrieg" in q or "war" in q or "krieg" in q:
        selected = [catalog[4], catalog[5], catalog[6], catalog[7], catalog[8]]
    else:
        selected = catalog[:6]

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
                "EU disintegration 2026 official statements Reuters",
                "EU member state exit risk 2026 Reuters AP",
                "European Commission EU unity press release",
            ]
        )

    if "weltkrieg" in q_lower or "world war" in q_lower:
        queries.extend(
            [
                "world war risk 2026 official Reuters AP AFP",
                "global conflict escalation 2026 Reuters AP AFP",
                "NATO UN global war warning Reuters",
                "major power conflict risk official statements Reuters",
            ]
        )

    if "election" in q_lower or "wahl" in q_lower:
        queries.extend(
            [
                "official election commission results Reuters AP AFP",
                "government election statement Reuters AP AFP",
            ]
        )

    # generische query-expansion
    queries.extend(
        [
            f"{q} official statements",
            f"{q} Reuters",
            f"{q} AP AFP",
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


def _select_balanced_sources(sources: List[SourceCandidate], max_sources: int) -> List[SourceCandidate]:
    by_type: Dict[str, List[SourceCandidate]] = {
        "official": [],
        "wire": [],
        "research": [],
        "major_media": [],
        "other": [],
    }
    for s in sorted(sources, key=lambda x: x.overall_score, reverse=True):
        by_type.setdefault(s.source_type, []).append(s)

    selected: List[SourceCandidate] = []

    # Mindestmix
    quotas = [
        ("official", 3),
        ("wire", 2),
        ("research", 2),
        ("major_media", 3),
    ]

    for source_type, quota in quotas:
        for item in by_type.get(source_type, [])[:quota]:
            if len(selected) >= max_sources:
                break
            selected.append(item)

    # Rest nach Score auffüllen
    selected_urls = {s.url for s in selected}
    remainder = [
        s
        for s in sorted(sources, key=lambda x: x.overall_score, reverse=True)
        if s.url not in selected_urls
    ]

    for item in remainder:
        if len(selected) >= max_sources:
            break
        selected.append(item)

    return selected[:max_sources]


def build_reasoning_from_sources(question_text: str, sources: List[SourceCandidate]) -> Dict[str, List[str]]:
    pro_points: List[str] = []
    contra_points: List[str] = []
    uncertainty_points: List[str] = []

    for s in sorted(sources, key=lambda x: x.overall_score, reverse=True):
        bullet = f"{s.publisher}: {s.title}"
        if s.stance == "pro" and bullet not in pro_points:
            pro_points.append(bullet)
        elif s.stance == "contra" and bullet not in contra_points:
            contra_points.append(bullet)
        elif s.stance in {"uncertainty", "neutral"} and bullet not in uncertainty_points:
            uncertainty_points.append(bullet)

    if not contra_points:
        contra_points.append("Mehrere höher gewichtete Quellen deuten eher auf institutionelle Kontinuität als auf ein unmittelbares Extremereignis hin.")
    if not pro_points:
        pro_points.append("Es gibt weiterhin Risikotreiber und Warnsignale, die das Eintreten des abgefragten Ereignisses nicht ausschließen.")
    if not uncertainty_points:
        uncertainty_points.append("Die Quellenlage enthält unvermeidbar Unsicherheit, insbesondere bei geopolitischen Schocks und schnellen Eskalationen.")

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
        qualifier = "derzeit ungefähr ausgeglichen"
    elif pct < 75:
        qualifier = "derzeit eher wahrscheinlich"
    else:
        qualifier = "derzeit klar wahrscheinlich"

    first_contra = reasoning.get("contra", ["Die höher gewichtete Quellenlage spricht eher gegen das Eintreten."])[0]
    return (
        f"Für die Frage „{question_text}“ erscheint das Ereignis mit {pct:.1f}% {qualifier}. "
        f"Zentral für diese Einschätzung ist: {first_contra}"
    )


def research_sources_for_question(
    question_text: str,
    *,
    max_sources: int = DEFAULT_MAX_SOURCES,
) -> Dict[str, Any]:
    queries = build_query_variants(question_text)
    gathered: List[SourceCandidate] = []

    # 1) feste offizielle Einstiegspunkte
    gathered.extend(_official_catalog_candidates(question_text))

    # 2) öffentliche Suchquellen
    for query in queries:
        gathered.extend(_fetch_gdelt_sources(query, question_text, max_records=6))
        gathered.extend(_fetch_google_news_rss(query, question_text, max_records=5))

    deduped = _dedupe_sources(gathered)
    selected = _select_balanced_sources(deduped, max_sources=max_sources)
    counts = _source_type_counts(selected)
    reasoning = build_reasoning_from_sources(question_text, selected)

    return {
        "question_text": question_text,
        "queries": queries,
        "sources": [asdict(s) for s in selected],
        "source_counts": counts,
        "reasoning": reasoning,
    }
