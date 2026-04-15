"""
Gemini-API-Integration für Claim-Extraktion und Forecast-Erklärung.
Verwendet das neue google-genai SDK (>= 1.0).

Alle Funktionen fallen auf regelbasierte Fallbacks zurück,
wenn kein API-Key gesetzt ist oder ein Fehler auftritt.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from app.core.logger import get_logger

log = get_logger("llm_service")

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

MODEL = "gemini-2.5-flash"

_CLAIM_EXTRACTION_SYSTEM = """\
You are a forecasting analyst. Extract claims from the given source that are relevant to the forecasting question.

For each relevant passage classify it as:
- "pro": supports the event happening
- "contra": supports the event NOT happening
- "uncertainty": ambiguous, conditional, or escalation risk
- "background": contextual but not directly relevant to the question

Return ONLY valid JSON in this exact shape:
{"claims": [{"claim_text": "...", "claim_type": "pro|contra|uncertainty|background", "claim_confidence": 0.0-1.0}]}

claim_confidence guidance (avoid 0.5 — be decisive):
- 0.80–0.95: strong factual claim with official source, confirmed numbers, or direct quotes
- 0.65–0.79: moderate evidence, credible reporting, likely accurate
- 0.40–0.64: weak signal, speculation, or indirect inference
- Use 0.30 or below for very weak/contradicted claims

Skip background claims. Keep claim_text concise (max 200 chars)."""

_EXPLANATION_SYSTEM_TEMPLATE = """\
You are a professional forecasting analyst. Write concise, data-driven forecast explanations.
Be direct, analytical and avoid excessive hedging. Use Markdown formatting.
{lang_instruction}"""

_LANG_INSTRUCTIONS: dict[str, str] = {
    "de": "Write in German (Deutsch).",
    "en": "Write in English.",
    "it": "Write in Italian (Italiano).",
    "fr": "Write in French (Français).",
    "es": "Write in Spanish (Español).",
}


def _get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def _parse_json_response(text: str) -> dict:
    """Robustes JSON-Parsing für Gemini-Antworten.
    Versucht direktes Parsen, dann Regex-Extraktion des ersten JSON-Objekts.
    """
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Gemini-2.5-flash kann Thinking-Tokens oder Extra-Text einbetten
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    log.warning("JSON-Parsing fehlgeschlagen, Fallback auf leeres Dict. Text-Anfang: %.100s", text)
    return {}


def _get_client() -> "genai.Client | None":
    if not _GENAI_AVAILABLE:
        log.warning("google-genai nicht installiert")
        return None
    api_key = _get_api_key()
    if not api_key:
        log.warning("GEMINI_API_KEY nicht gesetzt — LLM deaktiviert")
        return None
    return genai.Client(api_key=api_key)


def generate_search_queries(question_text: str) -> List[str]:
    """
    Generiert 4 gezielte Suchanfragen für eine Prognosefrage.
    Gibt leere Liste zurück wenn kein API-Key oder Fehler.
    """
    client = _get_client()
    if client is None:
        return []

    system = (
        "You are a research assistant helping gather evidence for a forecasting question. "
        "Generate exactly 4 short Google News search queries (2–5 words each) that cover "
        "different angles: the core event, opposing signals, expert/official statements, and recent developments. "
        'Return ONLY valid JSON: {"queries": ["q1", "q2", "q3", "q4"]}'
    )
    user_message = f'Forecasting question: "{question_text}"\n\nGenerate 4 search queries.'

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                max_output_tokens=256,
            ),
        )
        data = _parse_json_response(response.text or "")
        queries = data.get("queries", [])
        return [str(q).strip() for q in queries if str(q).strip()][:5]
    except Exception as exc:
        log.error("generate_search_queries fehlgeschlagen: %s", exc)
        return []


def extract_claims_with_llm(
    question_text: str,
    source: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extrahiert Claims aus einer Quelle mit Gemini.
    Gibt leere Liste zurück bei fehlendem Key oder Fehler.
    """
    client = _get_client()
    if client is None:
        return []

    title = (source.get("title") or "").strip()
    summary = (source.get("summary") or "").strip()
    excerpt = (source.get("excerpt") or "").strip()
    source_type = source.get("source_type") or "other"

    source_text = " ".join(filter(None, [title, summary, excerpt]))
    if not source_text:
        return []

    user_message = (
        f"Forecasting question: {question_text}\n\n"
        f"Source (type: {source_type}):\n{source_text}\n\n"
        "Extract relevant claims as JSON."
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=_CLAIM_EXTRACTION_SYSTEM,
                response_mime_type="application/json",
                max_output_tokens=1024,
            ),
        )

        data = _parse_json_response(response.text or "")
        freshness = float(source.get("freshness_score") or 0.45)
        source_url = source.get("url") or ""

        claims: List[Dict[str, Any]] = []
        for item in data.get("claims", []):
            if item.get("claim_type") == "background":
                continue
            claims.append(
                {
                    "claim_text": str(item.get("claim_text", "")).strip(),
                    "claim_type": str(item.get("claim_type", "uncertainty")),
                    "source_url": source_url,
                    "source_title": title,
                    "source_type": source_type,
                    "claim_confidence": float(item.get("claim_confidence", 0.5)),
                    "time_relevance": freshness,
                }
            )
        return claims

    except Exception as exc:
        log.error("extract_claims_with_llm fehlgeschlagen: %s", exc, exc_info=True)
        return []


def generate_direct_answer(
    question_text: str,
    probability: float,
    top_pro_claims: List[Dict[str, Any]],
    top_contra_claims: List[Dict[str, Any]],
    top_uncertainties: List[Dict[str, Any]],
    language: str = "de",
) -> Dict[str, Any]:
    """
    Generiert eine direkte, frage-spezifische Antwort mit Gemini.

    Geschlossene Fragen (Ja/Nein): klare Einschätzung mit Wahrscheinlichkeit.
    Offene Fragen (Was/Wie/Wann/Wer/Wo/Warum): 3-4 konkrete Szenarien/Möglichkeiten,
    gespeichert als JSON-Array in 'scenarios' und als Markdown in 'direct_answer'.

    Gibt leeres Dict zurück bei fehlendem Key oder Fehler.
    """
    client = _get_client()
    if client is None:
        return {}

    lang_instruction = _LANG_INSTRUCTIONS.get(language.lower(), _LANG_INSTRUCTIONS["de"])
    pct = round(probability * 100.0, 1)

    def _fmt(claims: List[Dict[str, Any]]) -> str:
        if not claims:
            return "–"
        return "\n".join(f"- {c.get('claim_text', '').strip()}" for c in claims[:4])

    system = f"""\
Du bist ein präziser Prognose-Analyst. {lang_instruction}

FRAGETYP erkennen:
- GESCHLOSSEN (Ja/Nein): beginnt mit Wird, Werden, Ist, Sind, Kann, Gibt es, Kommt es, Hat, Haben — oder ist klar mit Ja/Nein beantwortbar.
- OFFEN: beginnt mit Was, Wer, Wann, Wo, Wie, Warum, Welche, Wieviel, Womit, Wozu — oder fragt nach Wert, Zeitpunkt, Person, Ort, Menge, Ursache, Verlauf.

REGELN FÜR GESCHLOSSENE FRAGEN:
- Nutze die Wahrscheinlichkeit als Grundlage.
- Klare Einschätzung: wahrscheinlich ja / eher nein / unklar.
- Kurze Begründung aus den Signalen.
- JSON-Format:
{{
  "question_type": "closed",
  "direct_answer": "2-3 Sätze: Einschätzung + Begründung",
  "answer_label": "yes|lean_yes|uncertain|lean_no|no",
  "answer_confidence_band": "likely|moderate|close_call|unlikely",
  "answer_rationale_short": "Ein Satz Kernbegründung",
  "scenarios": []
}}

REGELN FÜR OFFENE FRAGEN:
- KEINE Wahrscheinlichkeit, KEIN Ja/Nein.
- Erstelle 3-4 konkrete, realistische Szenarien/Möglichkeiten als direkte Antwort auf die Frage.
- Jedes Szenario hat einen prägnanten Titel und 1-2 erklärende Sätze.
- Stütze dich auf die vorhandenen Signale und Quellen.
- JSON-Format:
{{
  "question_type": "open",
  "direct_answer": "Einleitender Satz der die wichtigsten Möglichkeiten zusammenfasst.",
  "answer_label": "analytical",
  "answer_confidence_band": "analytical",
  "answer_rationale_short": "Ein Satz warum diese Szenarien plausibel sind",
  "scenarios": [
    {{"title": "Szenario-Titel", "description": "1-2 Sätze Beschreibung"}},
    {{"title": "Szenario-Titel", "description": "1-2 Sätze Beschreibung"}},
    {{"title": "Szenario-Titel", "description": "1-2 Sätze Beschreibung"}}
  ]
}}

WICHTIG: Antworte AUSSCHLIESSLICH als gültiges JSON. Grammatikalisch korrekt, präzise, ohne Floskeln."""

    user_message = f"""\
Frage: {question_text}
Berechnete Wahrscheinlichkeit (nur für geschlossene Fragen relevant): {pct}%

Pro-Signale:
{_fmt(top_pro_claims)}

Contra-Signale:
{_fmt(top_contra_claims)}

Unsicherheiten:
{_fmt(top_uncertainties)}

Antworte als JSON."""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                max_output_tokens=8192,
            ),
        )
        data = _parse_json_response(response.text or "")

        if not data.get("direct_answer") or not data.get("answer_label"):
            return {}

        # Szenarien als Liste normalisieren
        raw_scenarios = data.get("scenarios") or []
        scenarios: List[Dict[str, str]] = []
        for s in raw_scenarios:
            if isinstance(s, dict) and s.get("title"):
                scenarios.append({
                    "title": str(s.get("title", "")).strip(),
                    "description": str(s.get("description", "")).strip(),
                })

        return {
            "direct_answer": str(data["direct_answer"]).strip(),
            "answer_label": str(data.get("answer_label", "uncertain")),
            "answer_confidence_band": str(data.get("answer_confidence_band", "close_call")),
            "answer_rationale_short": str(data.get("answer_rationale_short", "")).strip(),
            "question_type": str(data.get("question_type", "unknown")),
            "scenarios": scenarios,
        }

    except Exception as exc:
        log.error("generate_direct_answer fehlgeschlagen: %s", exc, exc_info=True)
        return {}


def estimate_base_rate(question_text: str) -> float:
    """
    Schätzt die historische Basisrate (Prior) für eine Prognosefrage via Gemini.
    Gibt 0.50 zurück wenn kein API-Key oder Fehler.

    Die Basisrate ist unabhängig von aktuellen Quellen — sie basiert auf
    historischen Häufigkeiten ähnlicher Ereignisse (z.B. Wahl von Amtsinhabern,
    Zinsentscheide, Militärkonflikte, Sportergebnisse).
    """
    client = _get_client()
    if client is None:
        return 0.50

    system = """\
You are a superforecaster calibration expert. For the given forecasting question, estimate the base rate probability — the historical frequency at which similar events occur, BEFORE looking at any current evidence.

Think about:
- The domain (politics, economics, sports, science, conflict, etc.)
- How often similar events have occurred historically
- Whether this is a status-quo vs. change question
- Known reference class frequencies

Base rate guidelines:
- Incumbent re-election / status quo continuation: 0.55–0.75
- Central bank rate changes in a given quarter: 0.30–0.55
- Sports favorites winning a championship: 0.25–0.50
- Major geopolitical escalation / war start: 0.05–0.20
- Catastrophic/existential events (nuclear war, etc.): 0.01–0.05
- Common policy reversals under political pressure: 0.25–0.45
- Court rulings against government: 0.20–0.40
- When genuinely uncertain and no reference class applies: 0.50

Return ONLY valid JSON: {"base_rate": 0.XX, "reference_class": "one sentence"}"""

    user_message = f'Forecasting question: "{question_text}"\n\nEstimate the base rate prior probability.'

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                max_output_tokens=128,
            ),
        )
        data = _parse_json_response(response.text or "")
        base_rate = data.get("base_rate")
        if base_rate is not None:
            value = float(base_rate)
            # Clamp to sensible range — never let the prior be too extreme
            return max(0.05, min(0.90, value))
    except Exception as exc:
        log.error("estimate_base_rate fehlgeschlagen: %s", exc)

    return 0.50


def generate_forecast_explanation(
    question_text: str,
    probability: float,
    top_pro_claims: List[Dict[str, Any]],
    top_contra_claims: List[Dict[str, Any]],
    top_uncertainties: List[Dict[str, Any]],
    sources: List[Dict[str, Any]],
    language: str = "de",
) -> str:
    """
    Generiert eine natürlichsprachliche Forecast-Erklärung mit Gemini.
    Gibt leeren String zurück bei fehlendem Key oder Fehler.
    """
    client = _get_client()
    if client is None:
        return ""

    lang_instruction = _LANG_INSTRUCTIONS.get(language.lower(), _LANG_INSTRUCTIONS["de"])
    system = _EXPLANATION_SYSTEM_TEMPLATE.format(lang_instruction=lang_instruction)

    pct = round(probability * 100.0, 1)

    def _fmt_claims(claims: List[Dict[str, Any]]) -> str:
        if not claims:
            return "Keine"
        return "\n".join(f"- {c.get('claim_text', '').strip()}" for c in claims)

    source_list = "\n".join(
        f"- {s.get('title') or s.get('url') or 'Unbekannte Quelle'} ({s.get('source_type', 'other')})"
        for s in sources[:6]
    )

    user_message = (
        f"**Frage:** {question_text}\n"
        f"**Berechnete Wahrscheinlichkeit:** {pct}%\n\n"
        f"**Pro-Signale (sprechen FÜR Eintreten):**\n{_fmt_claims(top_pro_claims)}\n\n"
        f"**Contra-Signale (sprechen GEGEN Eintreten):**\n{_fmt_claims(top_contra_claims)}\n\n"
        f"**Unsicherheiten:**\n{_fmt_claims(top_uncertainties)}\n\n"
        f"**Analysierte Quellen:**\n{source_list}\n\n"
        "Schreibe eine Forecast-Erklärung (3–4 Absätze, Markdown). "
        "Erkläre die Wahrscheinlichkeit anhand der Evidenz. Schließe mit einer kurzen Einschätzung."
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=1024,
            ),
        )
        return (response.text or "").strip()

    except Exception as exc:
        log.error("generate_forecast_explanation fehlgeschlagen: %s", exc, exc_info=True)
        return ""
