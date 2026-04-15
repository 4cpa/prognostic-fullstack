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
from concurrent.futures import ThreadPoolExecutor, as_completed


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
REQUEST_TIMEOUT = 12

# Language detection
_LANG_MARKERS: Dict[str, Tuple[str, ...]] = {
    "de": ("der", "die", "das", "ist", "und", "wird", "für", "nicht", "wir", "ich", "auf", "mit", "als",
           "oder", "dass", "sich", "auch", "beim", "vom", "zur", "nach", "wenn", "werden", "haben"),
    "fr": ("le", "la", "les", "est", "et", "pour", "dans", "qui", "que", "une", "avec", "sur", "au",
           "du", "pas", "plus", "nous", "sera", "sont", "quel", "quelle", "quels", "quelles", "très",
           "cette", "ces", "leur", "ils", "elle", "prochain", "prochaine", "dernier"),
    "it": ("il", "la", "gli", "per", "con", "che", "una", "del", "nei", "sono", "non", "questo",
           "dalla", "nella", "delle", "quale", "quando", "sarà", "hanno", "loro", "anche"),
    "es": ("el", "los", "para", "con", "que", "una", "del", "por", "nos", "como", "pero", "sus",
           "esto", "será", "han", "cuando", "qué", "cuándo", "próximo", "última", "también"),
}

_LANG_NEWS_PARAMS: Dict[str, Dict[str, str]] = {
    "de": {"hl": "de", "gl": "DE", "ceid": "DE:de"},
    "fr": {"hl": "fr", "gl": "FR", "ceid": "FR:fr"},
    "it": {"hl": "it", "gl": "IT", "ceid": "IT:it"},
    "es": {"hl": "es", "gl": "ES", "ceid": "ES:es"},
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
}


def _detect_language(text: str) -> str:
    words = set(re.findall(r'\b[a-zäöüàâéèêëïîôùûüçæœ]{2,}\b', text.lower()))
    scores = {lang: sum(1 for m in markers if m in words) for lang, markers in _LANG_MARKERS.items()}
    best_lang = max(scores, key=lambda l: scores[l])
    # Threshold 1 so single strong marker (e.g. "quel", "será") suffices for short questions
    return best_lang if scores[best_lang] >= 1 else "en"


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
    "ifo", "diw berlin", "bertelsmann", "swp berlin", "dgap", "snf", "nber",
    "imf.org", "worldbank.org", "piie.com", "wilsoncenter",
    "nature.com", "thelancet.com", "sciencemag.org", "newscientist.com",
    "scientificamerican.com", "pnas.org", "bmj.com",
)

# Nationale & regionale Medien (mittlere Glaubwürdigkeit)
NATIONAL_MEDIA_PUBLISHER_PATTERNS = (
    # DE/AT/CH
    "spiegel", "zeit.de", "faz.net", "sueddeutsche", "welt.de", "handelsblatt",
    "tagesspiegel", "focus.de", "stern.de", "nzz.ch", "tagesanzeiger", "blick.ch",
    "orf.at", "derstandard.at", "diepresse.com", "kurier.at",
    # FR
    "lemonde.fr", "lefigaro.fr", "liberation.fr", "franceinfo.fr", "lexpress.fr",
    "letemps.ch", "rts.ch", "rtbf.be",
    # IT
    "corriere.it", "repubblica.it", "lastampa.it", "ansa.it", "ilsole24ore.com",
    # ES/PT
    "elpais.com", "elmundo.es", "lavanguardia.com", "efe.com", "publico.pt",
    # PL/CZ/HU/RO
    "polsatnews.pl", "tvn24.pl", "novinky.cz", "index.hu", "digi24.ro",
    # UK/IE/AU/CA
    "independent.co.uk", "telegraph.co.uk", "mirror.co.uk", "thescotsman.com",
    "irishtimes.com", "rte.ie", "abc.net.au", "smh.com.au", "globeandmail.com", "torontostar.com",
    # ASIA/AFRICA/LATAM
    "nikkei.com", "scmp.com", "timesofindia.com", "thehindu.com",
    "dailynation.co.ke", "allafrica.com", "infobae.com", "eltiempo.com",
    # NORDICS/OTHERS
    "svt.se", "svd.se", "yle.fi", "nrk.no", "dr.dk", "bnn.gr",
)

# Alternative & weniger zuverlässige Quellen (geringe Glaubwürdigkeit)
ALTERNATIVE_PUBLISHER_PATTERNS = (
    "rt.com", "sputniknews", "sputnik", "tass.ru", "xinhua",
    "zerohedge", "breitbart", "epochtimes", "theepochtimes",
    "naturalnews", "globalresearch.ca", "infowars", "dailywire",
    "oann", "newsmax", "thegrayzone", "mintpressnews",
    "strategic-culture", "unz.com", "activistpost", "theduran",
    "southfront.org", "veteranstoday", "21stcenturywire",
)

# ---------------------------------------------------------------------------
# Themen-Erkennung
# ---------------------------------------------------------------------------

_KIND_PATTERNS: List[Tuple[str, Tuple[str, ...]]] = [
    ("existence", (
        " fort?", " fort ", "fortbestand", "fortbestehen", "weiterbestehen", "überleben",
        "bleibt bestehen", "löst sich auf", "wird aufgelöst",
        "dissolution", "will it survive", "still exist", "remain operational",
        "continue to exist", "disbands",
    )),
    ("world_war", ("weltkrieg", "world war", "dritter weltkrieg", "third world war")),
    ("war", ("krieg", " war ", "conflict", "military", "troops", "invasion", "nato", "ukraine", "gaza", "israel")),
    ("economics", (
        "stock", "aktie", "price", "preis", "market", "börse", "crypto", "bitcoin",
        "inflation", "recession", "gdp", "interest rate", "zinsen", "economy",
        "wirtschaft", "dax", "nasdaq", "s&p", "dollar", " euro ", "currency",
        "eurozone", "eurokurs",
    )),
    ("politics", (
        "election", "wahl", "president", "präsident", "chancellor", "kanzler",
        "parliament", "congress", "senate", "minister", "government", "regierung",
        "referendum", "abstimmung", "vote", "partei", "party",
        "uno", "united nations", "un ", "eu ", "european union", "europäische union",
        "trump", "biden", "putin", "xi jinping", "merkel", "scholz", "macron",
        "sanktion", "sanction", "diplomat", "treaty", "vertrag", "summit", "gipfel",
    )),
    ("technology", (
        " ai ", "artificial intelligence", "software", " app ", "tech startup",
        "apple", "google", "microsoft", "meta", "openai", "chip", "semiconductor",
        "smartphone", " ev ", "electric vehicle", "tesla", "iphone", "android",
        "roboter", "robot", "automation", "digitalisierung", "digitalization",
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
    ("education", (
        "schulreform", "bildungsreform", "lehrplan", "schule", "bildung", "hochschule",
        "universität", "pisa", "harmos", "bildungssystem", "schulpflicht", "gymnasium",
        "berufsbildung", "lehre", "lehrperson", "unterricht", "bildungspolitik",
        "school reform", "education reform", "curriculum", "school system", "university",
        "higher education", "vocational training", "education policy", "pedagogy",
        "teaching", "learning", "literacy", "edk", "sbfi", "skbf",
    )),
    ("culture", (
        "kunst", "musik", "film", "kino", "theater", "oper", "museum", "ausstellung",
        "literatur", "buch", "autor", "festival", "konzert", "kulturerbe",
        "art", "music", "cinema", "theatre", "opera", "museum", "exhibition",
        "literature", "book", "author", "festival", "concert", "heritage",
    )),
    ("media", (
        "zeitung", "fernsehen", "radio", "streaming", "soziale medien", "journalismus",
        "redaktion", "verlag", "medienkonzern", "pressewesen", "nachrichten",
        "newspaper", "television", "broadcasting", "streaming", "social media",
        "journalism", "editorial", "publisher", "media group", "press", "newsroom",
        "netflix", "spotify", "youtube", "tiktok", "instagram", "twitter", "x.com",
    )),
    ("industry", (
        "industrie", "fabrik", "produktion", "fertigung", "automobil", "auto",
        "stahl", "chemie", "pharma", "rüstung", "bergbau", "rohstoff",
        "industry", "factory", "production", "manufacturing", "automotive", "car",
        "steel", "chemical", "pharma", "defense", "mining", "raw material",
        "lieferkette", "supply chain", "export", "import", "zoll", "tariff",
    )),
    ("energy", (
        "energie", "strom", "gas", "öl", "kernkraft", "kernenergie", "solar", "windkraft",
        "kohle", "energiewende", "kraftwerk", "strommix", "gaspreise", "ölpreis",
        "energy transition", "electricity", "nuclear energy", "renewable energy",
        "power plant", "opec", " iea ", "lng", "pipeline", "power grid",
        "strompreis", "gasversorgung", "energieversorgung",
    )),
    ("science", (
        "forschung", "wissenschaft", "weltraum", "raumfahrt", "physik", "biologie",
        "genforschung", "quantencomputer", "nasa", "esa", "cern",
        "research", "science", "space", "physics", "biology", "genome",
        "quantum", "particle", "astronomy", "satellite", "rocket",
    )),
    ("finance", (
        "bank", "bankrott", "kredit", "zinsen", "immobilien", "fonds", "hedge",
        "versicherung", "rente", "pension", "dividende", "anleihe", "kapitalmarkt",
        "banking", "bankruptcy", "credit", "interest rate", "real estate", "fund",
        "insurance", "pension", "dividend", "bond", "capital market",
        "snb", "swiss national bank", "nationalbank",
    )),
    ("transport", (
        "flugzeug", "airline", "flughafen", "bahn", "zug", "schiff", "hafen",
        "autobahn", "verkehr", "logistik", "lieferdienst",
        "airline", "airport", "railway", "train", "ship", "port",
        "highway", "traffic", "logistics", "freight", "aviation",
        "swiss", "lufthansa", "sbb", "sncf", "db bahn",
    )),
    ("law", (
        "gericht", "urteil", "gesetz", "klage", "strafrecht", "verfassung",
        "bundesgericht", "europäischer gerichtshof", "menschenrechte",
        "court", "ruling", "judgment", "law", "legislation", "lawsuit", "criminal",
        "constitution", "supreme court", "echr", "human rights", "sentence",
    )),
    ("social", (
        "migration", "asyl", "flüchtling", "bevölkerung", "armut", "wohnen",
        "sozialversicherung", "rente", "altersvorsorge", "gleichstellung",
        "migration", "asylum", "refugee", "population", "poverty", "housing",
        "social security", "pension", "retirement", "gender equality",
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
    "existence": (
        # pro: institution ist aktiv, plant Zukunft, hält Konferenzen ab
        ("hosts", "convenes", "holds", "scheduled", "plans", "appoints", "elects",
         "meets", "adopts resolution", "treaty", "conference", "summit", "session",
         "operational", "active", "continues", "renewed", "reform", "strengthened",
         "budget approved", "member states", "general assembly", "security council"),
        # contra: Bedrohungen, Rückzug, Finanzierungskrise, Auflösungstendenzen
        ("dissolves", "disbanded", "collapse", "exit", "withdraw", "defunds",
         "funding cut", "leaves", "quits", "withdraws from", "sanctions", "veto blocks",
         "reform fails", "paralyzed", "ineffective", "obsolete", "abolished"),
    ),
    "world_war": (
        ("world war", "weltkrieg", "global war", "article 5", "major power", "direct conflict"),
        ("ceasefire", "de-escalation", "diplomacy", "negotiations", "peace", "containment"),
    ),
    "war": (
        ("offensive", "invasion", "attack", "airstrikes", "casualties", "escalation"),
        ("ceasefire", "peace talks", "withdrawal", "agreement", "truce", "mediation"),
    ),
    "culture": (
        ("opens", "launches", "awarded", "record attendance", "new exhibition", "premiere",
         "eröffnet", "ausgezeichnet", "rekordbesuch", "uraufführung"),
        ("closes", "cancelled", "funding cut", "protest", "controversy", "scandal",
         "schliesst", "abgesagt", "förderkürzung", "skandal"),
    ),
    "media": (
        ("growth", "record subscribers", "launches", "acquires", "partnership", "expands",
         "wachstum", "rekordabo", "übernimmt", "fusion"),
        ("layoffs", "shutdown", "decline", "loses", "censorship", "fine",
         "entlassungen", "schliessung", "rückgang", "zensur", "strafe"),
    ),
    "industry": (
        ("record output", "expansion", "investment", "orders", "growth", "profit",
         "rekordproduktion", "expansion", "investition", "aufträge"),
        ("decline", "plant closure", "layoffs", "strike", "shortage", "tariff",
         "rückgang", "werksschliessung", "entlassungen", "streik", "mangel"),
    ),
    "energy": (
        ("record output", "new capacity", "cheaper", "surplus", "expansion", "agreement",
         "rekord", "günstigerer", "überschuss"),
        ("shortage", "blackout", "price spike", "crisis", "sanction", "cut",
         "engpass", "stromausfall", "preisanstieg", "krise"),
    ),
    "science": (
        ("breakthrough", "discovery", "launch", "approved", "record", "milestone",
         "durchbruch", "entdeckung", "start", "genehmigt"),
        ("fails", "delayed", "cancelled", "budget cut", "explodes",
         "scheitert", "verzögert", "abgesagt", "budgetkürzung"),
    ),
    "finance": (
        ("profit", "record", "growth", "approved", "stable", "upgrade",
         "gewinn", "rekord", "wachstum", "stabil"),
        ("loss", "default", "fine", "scandal", "downgrade", "collapse",
         "verlust", "ausfall", "strafe", "skandal", "kollaps"),
    ),
    "transport": (
        ("new route", "expansion", "record passengers", "on time", "investment",
         "neue strecke", "expansion", "rekordpassagiere", "pünktlich"),
        ("strike", "delay", "cancellation", "crash", "shutdown", "fine",
         "streik", "verspätung", "ausfall", "absturz", "strafe"),
    ),
    "law": (
        ("upheld", "acquitted", "passed", "reform approved", "rights protected",
         "bestätigt", "freigesprochen", "verabschiedet", "rechte gestärkt"),
        ("convicted", "violated", "struck down", "appeal failed", "scandal",
         "verurteilt", "verletzt", "gekippt", "berufung abgelehnt"),
    ),
    "social": (
        ("integration", "increase benefits", "new housing", "reform passed", "rights expanded",
         "integration", "leistungserhöhung", "neuer wohnraum", "reform"),
        ("crisis", "cuts", "protest", "conflict", "shortage", "deportation",
         "krise", "kürzungen", "protest", "konflikt", "mangel", "abschiebung"),
    ),
    "education": (
        ("reform", "new curriculum", "overhaul", "restructure", "initiative", "pilot",
         "harmos", "new law", "bildungsreform", "lehrplanrevision", "neue schule"),
        ("no reform", "stalled", "blocked", "rejected", "failed", "cancelled",
         "keine reform", "gescheitert", "abgelehnt"),
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
    "education": 0.05,
    "culture": 0.05,
    "media": 0.05,
    "industry": 0.05,
    "energy": 0.06,
    "science": 0.05,
    "finance": 0.06,
    "transport": 0.05,
    "law": 0.05,
    "social": 0.05,
    "general": 0.05,
}

# Offizieller Quellen-Katalog nach Thema
# "universal" = wird für alle Themen eingebunden
OFFICIAL_SOURCES_CATALOG: Dict[str, List[Dict[str, str]]] = {
    "universal": [
        {"title": "UN News", "url": "https://news.un.org/en/", "publisher": "United Nations", "summary": "UN News"},
        {"title": "OECD News", "url": "https://www.oecd.org/newsroom/", "publisher": "OECD", "summary": "OECD official news and data"},
        {"title": "World Bank Blogs", "url": "https://blogs.worldbank.org/", "publisher": "World Bank", "summary": "World Bank research and analysis"},
        {"title": "IMF News", "url": "https://www.imf.org/en/News", "publisher": "IMF", "summary": "IMF press releases and statements"},
    ],
    "war": [
        {"title": "NATO News", "url": "https://www.nato.int/cps/en/natohq/news.htm", "publisher": "NATO", "summary": "NATO official news"},
        {"title": "U.S. State Department", "url": "https://www.state.gov/news/", "publisher": "U.S. State Department", "summary": "U.S. foreign policy news"},
        {"title": "EU External Action", "url": "https://www.eeas.europa.eu/eeas/news_en", "publisher": "EU External Action Service", "summary": "EU foreign policy and security news"},
        {"title": "ICRC News", "url": "https://www.icrc.org/en/news", "publisher": "ICRC", "summary": "International Committee of the Red Cross news"},
    ],
    "world_war": [
        {"title": "NATO News", "url": "https://www.nato.int/cps/en/natohq/news.htm", "publisher": "NATO", "summary": "NATO official news"},
        {"title": "U.S. State Department", "url": "https://www.state.gov/news/", "publisher": "U.S. State Department", "summary": "U.S. foreign policy news"},
        {"title": "UN Security Council", "url": "https://www.un.org/securitycouncil/", "publisher": "UN Security Council", "summary": "UN Security Council resolutions and news"},
        {"title": "OSCE News", "url": "https://www.osce.org/news", "publisher": "OSCE", "summary": "OSCE security news"},
    ],
    "economics": [
        {"title": "Eurostat", "url": "https://ec.europa.eu/eurostat/news/", "publisher": "Eurostat", "summary": "EU statistical office, economic data"},
        {"title": "Federal Reserve", "url": "https://www.federalreserve.gov/newsevents.htm", "publisher": "Federal Reserve", "summary": "U.S. central bank news"},
        {"title": "ECB Press", "url": "https://www.ecb.europa.eu/press/html/index.en.html", "publisher": "European Central Bank", "summary": "ECB monetary policy and press releases"},
        {"title": "Destatis", "url": "https://www.destatis.de/EN/Press/", "publisher": "Statistisches Bundesamt", "summary": "German Federal Statistical Office"},
        {"title": "BFS Medienmitteilungen", "url": "https://www.bfs.admin.ch/bfs/de/home/aktuell/neue-veroeffentlichungen.html", "publisher": "BFS", "summary": "Swiss Federal Statistical Office"},
        {"title": "ONS UK Statistics", "url": "https://www.ons.gov.uk/news/news", "publisher": "Office for National Statistics UK", "summary": "UK national statistics"},
        {"title": "WTO News", "url": "https://www.wto.org/english/news_e/news_e.htm", "publisher": "WTO", "summary": "World Trade Organization news"},
    ],
    "politics": [
        {"title": "European Commission News", "url": "https://ec.europa.eu/commission/presscorner/", "publisher": "European Commission", "summary": "EU Commission press releases"},
        {"title": "Bundesregierung", "url": "https://www.bundesregierung.de/breg-en/news", "publisher": "Bundesregierung", "summary": "German federal government news"},
        {"title": "Conseil fédéral suisse", "url": "https://www.admin.ch/gov/en/start/documentation/media-releases.html", "publisher": "Schweizer Bundesrat", "summary": "Swiss Federal Council press releases"},
        {"title": "UK Government News", "url": "https://www.gov.uk/search/news-and-communications", "publisher": "UK Government", "summary": "Official UK government news"},
        {"title": "Élysée Actualités", "url": "https://www.elysee.fr/en/news", "publisher": "Élysée", "summary": "French presidency news"},
        {"title": "White House Briefings", "url": "https://www.whitehouse.gov/briefing-room/", "publisher": "White House", "summary": "White House press briefings"},
        {"title": "Kremlin News", "url": "http://en.kremlin.ru/events/president/news", "publisher": "Kremlin", "summary": "Russian presidency news"},
        {"title": "MFA China", "url": "https://www.mfa.gov.cn/eng/", "publisher": "MFA China", "summary": "Chinese Ministry of Foreign Affairs"},
    ],
    "health": [
        {"title": "WHO News", "url": "https://www.who.int/news", "publisher": "WHO", "summary": "World Health Organization news"},
        {"title": "ECDC News", "url": "https://www.ecdc.europa.eu/en/news-events", "publisher": "ECDC", "summary": "European Centre for Disease Prevention and Control"},
        {"title": "CDC Newsroom", "url": "https://www.cdc.gov/media/index.html", "publisher": "CDC", "summary": "U.S. Centers for Disease Control and Prevention"},
        {"title": "BAG Schweiz", "url": "https://www.bag.admin.ch/bag/de/home/das-bag/aktuell/medienmitteilungen.html", "publisher": "BAG", "summary": "Bundesamt für Gesundheit Schweiz"},
        {"title": "RKI Meldungen", "url": "https://www.rki.de/DE/Content/Service/Presse/presse_node.html", "publisher": "RKI", "summary": "Robert Koch Institut Pressemitteilungen"},
    ],
    "climate": [
        {"title": "UNEP News", "url": "https://www.unep.org/news-and-stories/", "publisher": "UNEP", "summary": "UN Environment Programme news"},
        {"title": "IPCC Press", "url": "https://www.ipcc.ch/news-and-events/", "publisher": "IPCC", "summary": "Intergovernmental Panel on Climate Change"},
        {"title": "Copernicus Climate", "url": "https://climate.copernicus.eu/news-and-events", "publisher": "Copernicus/ECMWF", "summary": "EU climate data service"},
        {"title": "BAFU Schweiz", "url": "https://www.bafu.admin.ch/bafu/de/home/themen/klima/medienmitteilungen.html", "publisher": "BAFU", "summary": "Bundesamt für Umwelt Schweiz"},
        {"title": "UBA Deutschland", "url": "https://www.umweltbundesamt.de/presse/pressemitteilungen", "publisher": "Umweltbundesamt", "summary": "German Environment Agency"},
    ],
    "technology": [
        {"title": "ENISA News", "url": "https://www.enisa.europa.eu/news", "publisher": "ENISA", "summary": "EU Agency for Cybersecurity"},
        {"title": "SECO Digitalisierung", "url": "https://www.seco.admin.ch/seco/de/home/seco/nsb-news.html", "publisher": "SECO", "summary": "Swiss State Secretariat for Economic Affairs"},
    ],
    "education": [
        {"title": "EDK Medienmitteilungen", "url": "https://www.edk.ch/de/aktuell/medienmitteilungen", "publisher": "EDK", "summary": "Schweizerische Konferenz der kantonalen Erziehungsdirektoren"},
        {"title": "SBFI News", "url": "https://www.sbfi.admin.ch/sbfi/de/home/aktuell/medienmitteilungen.html", "publisher": "SBFI", "summary": "Staatssekretariat für Bildung, Forschung und Innovation Schweiz"},
        {"title": "SKBF Bildungsbericht", "url": "https://www.skbf-csre.ch/bildungsbericht/", "publisher": "SKBF", "summary": "Swiss Coordination Centre for Research in Education"},
        {"title": "KMK Pressemitteilungen", "url": "https://www.kmk.org/presse/pressemitteilungen.html", "publisher": "KMK", "summary": "Kultusministerkonferenz Deutschland"},
        {"title": "BMBF Nachrichten", "url": "https://www.bmbf.de/bmbf/de/home/presse/pressemitteilungen.html", "publisher": "BMBF", "summary": "Bundesministerium für Bildung und Forschung Deutschland"},
        {"title": "UNESCO Education", "url": "https://www.unesco.org/en/education/news", "publisher": "UNESCO", "summary": "UNESCO education news and policy"},
        {"title": "PISA OECD", "url": "https://www.oecd.org/pisa/", "publisher": "OECD PISA", "summary": "PISA international education assessment"},
    ],
    "existence": [
        {"title": "UN General Assembly", "url": "https://www.un.org/en/ga/", "publisher": "UN General Assembly", "summary": "UN General Assembly news and resolutions"},
        {"title": "European Parliament", "url": "https://www.europarl.europa.eu/news/en/", "publisher": "European Parliament", "summary": "EU Parliament news"},
    ],
    "culture": [
        {"title": "UNESCO Culture", "url": "https://www.unesco.org/en/culture/news", "publisher": "UNESCO", "summary": "UNESCO culture news"},
        {"title": "BAK Schweiz", "url": "https://www.bak.admin.ch/bak/de/home/aktuell/medienmitteilungen.html", "publisher": "BAK", "summary": "Bundesamt für Kultur Schweiz"},
        {"title": "Kulturstaatsministerium DE", "url": "https://www.bundesregierung.de/breg-de/themen/kultur-und-medien", "publisher": "Kulturstaatsministerium", "summary": "Deutsche Kulturpolitik"},
    ],
    "media": [
        {"title": "Reuters Institute", "url": "https://reutersinstitute.politics.ox.ac.uk/news", "publisher": "Reuters Institute", "summary": "Global journalism and media research"},
        {"title": "EBU News", "url": "https://www.ebu.ch/news", "publisher": "EBU", "summary": "European Broadcasting Union news"},
        {"title": "Ofcom News", "url": "https://www.ofcom.org.uk/news", "publisher": "Ofcom", "summary": "UK media regulator news"},
    ],
    "industry": [
        {"title": "ILO News", "url": "https://www.ilo.org/global/about-the-ilo/newsroom/news/lang--en/index.htm", "publisher": "ILO", "summary": "International Labour Organization news"},
        {"title": "WEF Industry", "url": "https://www.weforum.org/agenda/industry/", "publisher": "WEF", "summary": "World Economic Forum industry news"},
        {"title": "OECD Industry", "url": "https://www.oecd.org/industry/", "publisher": "OECD Industry", "summary": "OECD industry and enterprise statistics"},
        {"title": "SECO Industrie", "url": "https://www.seco.admin.ch/seco/de/home/Standortfoerderung/Wirtschaftspolitik.html", "publisher": "SECO", "summary": "Swiss economic and industry policy"},
    ],
    "energy": [
        {"title": "IEA News", "url": "https://www.iea.org/news", "publisher": "IEA", "summary": "International Energy Agency news"},
        {"title": "IAEA News", "url": "https://www.iaea.org/newscenter/news", "publisher": "IAEA", "summary": "International Atomic Energy Agency news"},
        {"title": "IRENA News", "url": "https://www.irena.org/News", "publisher": "IRENA", "summary": "International Renewable Energy Agency news"},
        {"title": "Elcom Schweiz", "url": "https://www.elcom.admin.ch/elcom/de/home/dokumentation/medienmitteilungen.html", "publisher": "ElCom", "summary": "Schweizer Elektrizitätskommission"},
        {"title": "Bundesnetzagentur DE", "url": "https://www.bundesnetzagentur.de/DE/Allgemeines/Presse/news.html", "publisher": "Bundesnetzagentur", "summary": "German energy and network regulator"},
    ],
    "science": [
        {"title": "NASA News", "url": "https://www.nasa.gov/news/", "publisher": "NASA", "summary": "NASA space and science news"},
        {"title": "ESA News", "url": "https://www.esa.int/Newsroom", "publisher": "ESA", "summary": "European Space Agency news"},
        {"title": "CERN Press", "url": "https://press.cern/news", "publisher": "CERN", "summary": "CERN particle physics news"},
        {"title": "Nature News", "url": "https://www.nature.com/news", "publisher": "Nature", "summary": "Nature scientific news"},
        {"title": "SNF Medienmitteilungen", "url": "https://www.snf.ch/de/aktuelles/medienmitteilungen/", "publisher": "SNF", "summary": "Schweizerischer Nationalfonds Medienmitteilungen"},
    ],
    "finance": [
        {"title": "BIS News", "url": "https://www.bis.org/press/", "publisher": "BIS", "summary": "Bank for International Settlements press"},
        {"title": "FINMA Medienmitteilungen", "url": "https://www.finma.ch/de/news/medienmitteilungen/", "publisher": "FINMA", "summary": "Schweizer Finanzmarktaufsicht"},
        {"title": "SNB News", "url": "https://www.snb.ch/de/mmr/reference/pre_2024/source.en.html", "publisher": "SNB", "summary": "Swiss National Bank news"},
        {"title": "FSB Press", "url": "https://www.fsb.org/press/", "publisher": "FSB", "summary": "Financial Stability Board press releases"},
        {"title": "BaFin News", "url": "https://www.bafin.de/DE/Presse/Pressemitteilungen/pressemitteilungen_node.html", "publisher": "BaFin", "summary": "German financial regulator news"},
    ],
    "transport": [
        {"title": "ICAO News", "url": "https://www.icao.int/Newsroom/Pages/default.aspx", "publisher": "ICAO", "summary": "International Civil Aviation Organization news"},
        {"title": "ITF-OECD Transport", "url": "https://www.itf-oecd.org/news", "publisher": "ITF-OECD", "summary": "International Transport Forum news"},
        {"title": "EASA News", "url": "https://www.easa.europa.eu/en/newsroom-and-events/news", "publisher": "EASA", "summary": "European Aviation Safety Agency news"},
        {"title": "ASTRA Schweiz", "url": "https://www.astra.admin.ch/astra/de/home/themen/netzentwicklung/medienmitteilungen.html", "publisher": "ASTRA", "summary": "Bundesamt für Strassen Schweiz"},
    ],
    "law": [
        {"title": "ECHR Press", "url": "https://www.echr.coe.int/pages/home.aspx?p=press", "publisher": "ECHR", "summary": "European Court of Human Rights press"},
        {"title": "ICJ News", "url": "https://www.icj-cij.org/press-releases", "publisher": "ICJ", "summary": "International Court of Justice press releases"},
        {"title": "Bundesgericht CH", "url": "https://www.bger.ch/index/press/press-inherit-template/pressPublications.htm", "publisher": "Bundesgericht", "summary": "Schweizer Bundesgericht Medienmitteilungen"},
        {"title": "EuGH Pressemitteilungen", "url": "https://curia.europa.eu/jcms/jcms/Jo2_7052/", "publisher": "EuGH", "summary": "Europäischer Gerichtshof Pressemitteilungen"},
    ],
    "social": [
        {"title": "UNHCR News", "url": "https://www.unhcr.org/news/", "publisher": "UNHCR", "summary": "UN Refugee Agency news"},
        {"title": "IOM News", "url": "https://www.iom.int/news", "publisher": "IOM", "summary": "International Organization for Migration news"},
        {"title": "SEM Schweiz", "url": "https://www.sem.admin.ch/sem/de/home/sem/aktuell/medienmitteilungen.html", "publisher": "SEM", "summary": "Staatssekretariat für Migration Schweiz"},
        {"title": "BAMF Nachrichten", "url": "https://www.bamf.de/DE/Presse/Pressemitteilungen/pressemitteilungen-node.html", "publisher": "BAMF", "summary": "Bundesamt für Migration und Flüchtlinge DE"},
    ],
}

# Rückwärtskompatibilität
GEOPOLITICAL_OFFICIAL_SOURCES = OFFICIAL_SOURCES_CATALOG["war"]


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


_OFFICIAL_DOMAIN_SUFFIXES = (
    ".gov", ".int", ".mil",
    ".gov.uk", ".gov.au", ".gov.ca", ".gov.nz", ".gov.za", ".gov.in",
    ".gob.es", ".gob.mx", ".gob.ar", ".gob.cl",
    ".gouv.fr", ".gouvernement.fr",
    ".gc.ca",
    ".gv.at",
)

_OFFICIAL_DOMAIN_SUBSTRINGS = (
    ".admin.ch", ".bund.de", "bundesregierung.de", "bundestag.de",
    "bundesrat.de", "bundesbank.de", "bafin.de", "destatis.de",
    "rki.de", "bka.de", "bsi.bund.de", "umweltbundesamt.de",
    "elysee.fr", "senat.fr", "assemblee-nationale.fr",
    "europarl.europa.eu", "ec.europa.eu", "eeas.europa.eu",
    "ecb.europa.eu", "eurostat.ec.europa.eu",
    "who.int", "un.org", "nato.int", "osce.org", "icrc.org",
    "imf.org", "worldbank.org", "oecd.org", "wto.org",
    "fed.us", "federalreserve.gov", "treasury.gov", "state.gov",
    "whitehouse.gov", "cdc.gov", "fda.gov", "epa.gov",
    "kremlin.ru", "mid.ru", "mfa.gov.cn", "gov.cn",
    "bag.admin.ch", "bafu.admin.ch", "bfs.admin.ch", "seco.admin.ch",
    "ons.gov.uk", "bankofengland.co.uk",
    "statistik.at", "oesterreichischebundesbank.at",
    "insee.fr", "banque-france.fr",
    "istat.it", "bancaditalia.it",
    "ine.es", "bde.es",
    "statistics.gov.scot", "statssa.gov.za",
    "abs.gov.au", "rba.gov.au",
)


def _publisher_type(publisher: str, domain: str) -> str:
    publisher_text = _lower(f"{publisher} {domain}")

    # Alternative Quellen zuerst prüfen (explizite Liste hat Vorrang)
    if any(p in publisher_text for p in ALTERNATIVE_PUBLISHER_PATTERNS):
        return "alternative"

    if any(p in publisher_text for p in AGGREGATOR_PUBLISHER_PATTERNS):
        return "aggregator"
    if any(p in publisher_text for p in RESEARCH_PUBLISHER_PATTERNS):
        return "research"
    if any(p in publisher_text for p in WIRE_PUBLISHER_PATTERNS):
        return "wire"
    if any(p in publisher_text for p in MAJOR_MEDIA_PUBLISHER_PATTERNS):
        return "major_media"

    # Offizielle Domains: TLD-Suffix und bekannte Substrings
    d = _lower(domain)
    if any(d.endswith(sfx) for sfx in _OFFICIAL_DOMAIN_SUFFIXES):
        return "official"
    if any(sub in d for sub in _OFFICIAL_DOMAIN_SUBSTRINGS):
        return "official"

    if any(p in publisher_text for p in NATIONAL_MEDIA_PUBLISHER_PATTERNS):
        return "national_media"

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
        "national_media": 0.20,
        "other": 0.18,
        "aggregator": 0.05,
        "alternative": 0.10,
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
    if source_type == "national_media":
        return 0.72
    if source_type == "aggregator":
        return 0.35
    if source_type == "alternative":
        return 0.28
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
        "alternative": -0.15,
        "other": 0.0,
        "national_media": 0.01,
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

_DE_STOPWORDS = frozenset({
    # Hilfsverben / Modalverben
    "wird", "besteht", "ist", "hat", "kann", "haben", "sein", "werden",
    "wurde", "waren", "wäre", "wären", "hätte", "hätten", "könnte", "könnten",
    "sollte", "sollten", "dürfte", "dürften", "müsste", "müssten",
    "gibt", "findet", "statt", "kommt", "geht",
    # Fragewörter
    "wann", "ob", "wie", "was", "wer", "wo", "wohin", "woher", "warum", "wieso",
    # Artikel / Pronomen
    "der", "die", "das", "ein", "eine", "einem", "einer", "den", "dem",
    "er", "sie", "es", "wir", "ihr", "sie", "sich", "man",
    # Präpositionen / Konjunktionen
    "und", "oder", "aber", "als", "für", "von", "mit", "bei", "im", "in",
    "an", "auf", "über", "unter", "durch", "nach", "vor", "bis", "ab",
    "noch", "fort", "weiter", "weiterhin", "bis zum", "bis zur", "bis zu",
    # Häufige Adjektive ohne Inhaltswert
    "nächste", "nächsten", "nächster", "letzte", "letzten", "letzter",
    "erste", "ersten", "erster", "neue", "neuen", "neuer", "große", "großen",
    "kleine", "kleinen", "weitere", "weiteren",
    # Sonstige
    "besteht die", "wird es", "gibt es", "wird der", "wird die", "wird das",
    "bleibt", "fort",
})

_DE_EN_MAP = {
    "uno": "United Nations",
    "eu": "European Union",
    "usa": "United States",
    "brd": "Germany",
    "bundesregierung": "German government",
    "bundestag": "German parliament",
    "aktie": "stock",
    "börse": "stock market",
    "wahl": "election",
    "krieg": "war",
    "frieden": "peace",
    "vertrag": "treaty",
    "sanktion": "sanctions",
    "wirtschaft": "economy",
    "inflation": "inflation",
    "rezession": "recession",
    "klimawandel": "climate change",
    "pandemie": "pandemic",
    "impfstoff": "vaccine",
    # Bildung
    "schulreform": "school reform",
    "bildungsreform": "education reform",
    "lehrplan": "curriculum",
    "schule": "school",
    "bildung": "education",
    "hochschule": "university",
    "universität": "university",
    "bildungssystem": "education system",
    "bildungspolitik": "education policy",
    "berufsbildung": "vocational training",
    "unterricht": "teaching",
    # Allgemein nützlich
    "schweiz": "Switzerland",
    "deutschland": "Germany",
    "österreich": "Austria",
    "frankreich": "France",
    "italien": "Italy",
    "bundestag": "German parliament",
    "nationalrat": "Swiss parliament",
    "regierung": "government",
    "reform": "reform",
    "gesetz": "law",
    "volksinitiative": "popular initiative Switzerland",
    "referendum": "referendum",
    # Kultur
    "film": "film",
    "kino": "cinema",
    "theater": "theatre",
    "oper": "opera",
    "konzert": "concert",
    "ausstellung": "exhibition",
    "festival": "festival",
    "literatur": "literature",
    # Medien
    "zeitung": "newspaper",
    "fernsehen": "television",
    "streaming": "streaming",
    "journalismus": "journalism",
    # Industrie
    "industrie": "industry",
    "fabrik": "factory",
    "produktion": "production",
    "automobil": "automotive",
    "stahl": "steel",
    # Energie
    "energie": "energy",
    "strom": "electricity",
    "kernkraft": "nuclear energy",
    "kohle": "coal",
    "energiewende": "energy transition",
    # Wissenschaft
    "forschung": "research",
    "wissenschaft": "science",
    "weltraum": "space",
    "raumfahrt": "space travel",
    # Finanzen
    "bank": "bank",
    "kredit": "credit",
    "immobilien": "real estate",
    "versicherung": "insurance",
    "anleihe": "bond",
    # Verkehr / Transport
    "flugzeug": "aircraft",
    "airline": "airline",
    "flughafen": "airport",
    "eisenbahn": "railway",
    "schifffahrt": "shipping",
    # Recht
    "gericht": "court",
    "urteil": "ruling",
    "klage": "lawsuit",
    "gesetz": "law",
    "verfassung": "constitution",
    # Soziales
    "migration": "migration",
    "asyl": "asylum",
    "flüchtling": "refugee",
    "armut": "poverty",
    "wohnen": "housing",
    "rente": "pension",
    # Länder / Regionen
    "italien": "Italy",
    "spanien": "Spain",
    "russland": "Russia",
    "china": "China",
    "japan": "Japan",
    "usa": "United States",
    "grossbritannien": "United Kingdom",
    "england": "England",
    "kanada": "Canada",
    "australien": "Australia",
    "europa": "Europe",
    "asien": "Asia",
    "naher osten": "Middle East",
    # Allgemein
    "zukunft": "future",
    "prognose": "forecast",
    "entwicklung": "development",
    "veränderung": "change",
    "krise": "crisis",
    "wachstum": "growth",
    "rückgang": "decline",
    "nächste": "next",  # keep as hint
}


def _extract_keywords(question_text: str) -> List[str]:
    """Extrahiert aussagekräftige Schlagworte aus einer Frage."""
    text = re.sub(r"[?!.,;:\"'()]", " ", question_text)
    text = re.sub(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", "", text)  # Daten entfernen
    words = text.split()

    keywords: List[str] = []
    for w in words:
        w_lower = w.lower()
        if w_lower in _DE_STOPWORDS or len(w) <= 2:
            continue
        translated = _DE_EN_MAP.get(w_lower)
        if translated:
            keywords.append(translated)
        elif w[0].isupper() and not re.match(r"^\d{4}$", w):
            # Kapitalisiertes Wort (Eigenname, Substantiv)
            keywords.append(w)
        elif len(w) >= 6 and w_lower not in _DE_STOPWORDS:
            # Längere Kleinbuchstaben-Wörter als Fallback (z.B. "schulreform" am Satzanfang)
            keywords.append(w)

    # Jahrzahl extrahieren falls vorhanden
    years = re.findall(r"\b(20\d{2})\b", question_text)

    seen: set = set()
    unique: List[str] = []
    for k in keywords:
        if k.lower() not in seen:
            seen.add(k.lower())
            unique.append(k)

    return unique[:6], years[:1]


def _query_plan_fallback(question_text: str) -> List[str]:
    """Regelbasierter Fallback falls kein LLM verfügbar.
    Generiert kurze, suchoptimierte Queries statt des vollen Fragesatzes."""
    kind = _question_kind(question_text)
    keywords, years = _extract_keywords(question_text)
    year = years[0] if years else ""

    kw_str = " ".join(keywords[:4])
    kw_short = " ".join(keywords[:2])

    if kind == "world_war":
        return [
            "world war risk 2026 Reuters AP AFP official",
            "diplomatic efforts avoid wider war Reuters",
            "NATO UN major power conflict warning",
            "global war escalation risk Reuters AP",
        ]
    def _with_year(s: str) -> str:
        return f"{s} {year}".strip() if year and year not in s else s

    if kind == "existence":
        # Fragen über Fortbestand: zuerst nach Aktivität, dann nach Bedrohungen suchen
        entity = " ".join(keywords[:2]) if keywords else question_text[:30]
        return [
            f"{entity} future {year}".strip() if year else f"{entity} future",
            f"{entity} dissolution threat",
            f"{entity} funding crisis reform",
            f"{entity} continues operations",
        ]
    if kind == "war":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} ceasefire", f"{base} Reuters", f"{kw_short} diplomacy".strip()]
    if kind == "economics":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} Reuters", _with_year(f"{kw_short} forecast"), f"{kw_short} analyst outlook"]
    if kind == "politics":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} Reuters", f"{kw_short} future outlook", f"{base} AP news"]
    if kind == "technology":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} announcement", f"{base} Reuters"]
    if kind == "health":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} study results", f"{base} WHO FDA"]
    if kind == "sports":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} results", f"{base} championship"]
    if kind == "culture":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} festival award", f"{base} news"]
    if kind == "media":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} Reuters", f"{base} industry news"]
    if kind == "industry":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} Reuters", _with_year(f"{kw_short} production forecast")]
    if kind == "energy":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} IEA Reuters", _with_year(f"{kw_short} price forecast")]
    if kind == "science":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} NASA ESA research", f"{base} breakthrough"]
    if kind == "finance":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} Reuters Bloomberg", _with_year(f"{kw_short} forecast")]
    if kind == "transport":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} Reuters", f"{base} ICAO IATA"]
    if kind == "law":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} court ruling", f"{base} Reuters law"]
    if kind == "social":
        base = kw_str or question_text[:40]
        return [_with_year(base), f"{base} UN UNHCR Reuters", _with_year(f"{kw_short} policy")]
    if kind == "education":
        base = kw_str or question_text[:40]
        return [
            _with_year(base),
            f"{base} reform EDK SBFI",
            f"{base} Bildungspolitik Schweiz" if "schweiz" in _lower(question_text) or "swiss" in _lower(question_text) else f"{base} education policy",
            f"{kw_short} Lehrplan Bildungsreform",
        ]

    # General fallback: use both extracted keywords AND full question text
    base = kw_str if kw_str else question_text[:60]
    raw_q = question_text.strip().rstrip("?").strip()[:80]
    queries = [_with_year(base)]
    if base != raw_q:
        queries.append(raw_q)
    queries.append(f"{base} Reuters")
    if kw_short:
        queries.append(f"{kw_short} news forecast")
    return queries


def _query_plan(question_text: str) -> List[str]:
    """Generiert Suchanfragen regelbasiert (kein LLM-Call, spart Quota)."""
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


def _google_news_search(query: str, *, limit: int = 15, hl: str = "en-US", gl: str = "US", ceid: str = "US:en") -> List[Dict[str, Any]]:
    params = {"q": query, "hl": hl, "gl": gl, "ceid": ceid}
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
    """Offizielle Quellen für alle Themen einbinden (universal + themenspezifisch)."""
    kind = _question_kind(question_text)

    catalog_entries = list(OFFICIAL_SOURCES_CATALOG.get("universal", []))
    catalog_entries += OFFICIAL_SOURCES_CATALOG.get(kind, [])

    # Duplikate nach URL entfernen
    seen_urls: set = set()
    unique_entries = []
    for entry in catalog_entries:
        u = entry["url"]
        if u not in seen_urls:
            seen_urls.add(u)
            unique_entries.append(entry)

    results: List[ResearchSource] = []
    for item in unique_entries:
        # Themenspezifische Relevanz: universal-Quellen etwas niedriger
        if item in OFFICIAL_SOURCES_CATALOG.get("universal", []):
            relevance = 0.06
        elif kind == "world_war":
            relevance = 0.08
        else:
            relevance = 0.12
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
    # Alternative Quellen: niedrigere Mindest-Relevanz, aber trotzdem einbinden
    alternative_mode = source_type == "alternative"

    relevance = _question_specific_relevance(question_text, title, summary)
    kind = _question_kind(question_text)
    min_rel = MIN_RELEVANCE_BY_KIND.get(kind, 0.05)
    # Alternative Quellen erhalten halbierte Mindest-Relevanz
    if alternative_mode:
        min_rel = min_rel * 0.5

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
    """Sucht in ALLEN verfügbaren Sprachen parallel für maximale Abdeckung."""
    queries = _query_plan(question_text)
    lang = _detect_language(question_text)
    native_params = _LANG_NEWS_PARAMS.get(lang, _LANG_NEWS_PARAMS["en"])

    # Alle (query, lang_params)-Paare aufbauen — jede Query in jeder Sprache
    search_tasks: List[tuple] = []
    for query in queries:
        for lang_params in _LANG_NEWS_PARAMS.values():
            search_tasks.append((query, lang_params, 8))

    # Rohe Frage zusätzlich in Muttersprache suchen
    raw_query = question_text.strip().rstrip("?").strip()[:120]
    if raw_query:
        search_tasks.append((raw_query, native_params, 10))

    def _search(args: tuple) -> List[Dict[str, Any]]:
        query, params, limit = args
        try:
            return _google_news_search(query, limit=limit, **params)
        except Exception:
            return []

    raw_items: List[Dict[str, Any]] = []
    # Parallel ausführen mit max. 12 gleichzeitigen Requests
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(_search, task) for task in search_tasks]
        for future in as_completed(futures, timeout=REQUEST_TIMEOUT + 5):
            try:
                raw_items.extend(future.result())
            except Exception:
                pass

    normalized: List[ResearchSource] = []
    for item in raw_items:
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
