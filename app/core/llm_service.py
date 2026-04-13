"""
Claude-API-Integration für Claim-Extraktion und Forecast-Erklärung.

Beide Funktionen fallen auf die regelbasierte Pipeline zurück,
wenn kein API-Key gesetzt ist oder ein Fehler auftritt.
"""
from __future__ import annotations

import json
import os
from contextvars import ContextVar
from typing import Any, Dict, List

try:
    import anthropic as _anthropic_module
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

MODEL = "claude-opus-4-6"

# Request-scoped API-Key (wird pro Request gesetzt, überschreibt Umgebungsvariable)
_request_api_key: ContextVar[str] = ContextVar("request_api_key", default="")


def set_request_api_key(key: str) -> None:
    """Setzt den API-Key für den aktuellen Request-Kontext."""
    _request_api_key.set(key.strip())

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

_EXPLANATION_SYSTEM = """\
Du bist ein professioneller Prognose-Analyst. Schreibe prägnante, datenbasierte Forecast-Erklärungen auf Deutsch.
Sei direkt, analytisch und vermeide übermäßige Absicherungen. Nutze Markdown-Formatierung."""


def _get_client() -> "anthropic.Anthropic | None":
    if not _ANTHROPIC_AVAILABLE:
        return None
    # Request-scoped Key hat Vorrang vor Umgebungsvariable
    api_key = _request_api_key.get("") or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    return _anthropic_module.Anthropic(api_key=api_key)


def extract_claims_with_llm(
    question_text: str,
    source: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extrahiert Claims aus einer Quelle mit Claude.

    Gibt eine leere Liste zurück wenn kein API-Key verfügbar
    oder ein Fehler auftritt (Fallback auf regelbasierte Logik).
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
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _CLAIM_EXTRACTION_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "claims": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "claim_text": {"type": "string"},
                                        "claim_type": {
                                            "type": "string",
                                            "enum": ["pro", "contra", "uncertainty", "background"],
                                        },
                                        "claim_confidence": {"type": "number"},
                                    },
                                    "required": ["claim_text", "claim_type", "claim_confidence"],
                                    "additionalProperties": False,
                                },
                            }
                        },
                        "required": ["claims"],
                        "additionalProperties": False,
                    },
                }
            },
        )

        text = next((b.text for b in response.content if b.type == "text"), "{}")
        data = json.loads(text)

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

    except Exception:
        return []


def generate_forecast_explanation(
    question_text: str,
    probability: float,
    top_pro_claims: List[Dict[str, Any]],
    top_contra_claims: List[Dict[str, Any]],
    top_uncertainties: List[Dict[str, Any]],
    sources: List[Dict[str, Any]],
) -> str:
    """
    Generiert eine natürlichsprachliche Forecast-Erklärung mit Claude.

    Gibt einen leeren String zurück bei fehlendem API-Key oder Fehler
    (Fallback auf Template-basierte Erklärung in forecast_engine.py).
    """
    client = _get_client()
    if client is None:
        return ""

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
        parts: List[str] = []
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _EXPLANATION_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for chunk in stream.text_stream:
                parts.append(chunk)
        return "".join(parts).strip()

    except Exception:
        return ""
