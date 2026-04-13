"""
Gemini-API-Integration für Claim-Extraktion und Forecast-Erklärung.
Verwendet das neue google-genai SDK (>= 1.0).

Alle Funktionen fallen auf regelbasierte Fallbacks zurück,
wenn kein API-Key gesetzt ist oder ein Fehler auftritt.
"""
from __future__ import annotations

import json
import os
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
        data = json.loads(response.text or "{}")
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

        data = json.loads(response.text or "{}")
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
