#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reliability & Regression Test fuer 4cpa Prognostic Engine
Keine externen Abhaengigkeiten – nur Python-Standardbibliothek.

Usage:
    python3 scripts/reliability_test.py              # Live-Site
    python3 scripts/reliability_test.py --local      # localhost:8000
    python3 scripts/reliability_test.py --quick      # nur 3 Fragen
    python3 scripts/reliability_test.py --verbose    # Diagnostics ausgeben
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

LIVE_BASE   = "https://4cpa.org/api"
LOCAL_BASE  = "http://localhost:8000"
TIMEOUT     = 90           # Sekunden pro Request
P50_BAND    = (0.43, 0.57) # Wahrscheinlichkeiten in diesem Band = 50%-Bias
P50_MAX_SHARE = 0.30       # Max. Anteil ~50%-Ergebnisse

# Fragen: expected_direction = "high" > 0.60 | "low" < 0.40 | "open" = egal
TEST_QUESTIONS = [
    {
        "text": "Wird die Schweiz bis 2030 der EU beitreten?",
        "expected_direction": "low",
        "reason": "Historisch sehr unwahrscheinlich; mehrfache Volksabstimmungen dagegen",
    },
    {
        "text": "Wird Cristiano Ronaldo 2025 noch Profi-Fussball spielen?",
        "expected_direction": "high",
        "reason": "Er spielte 2025 aktiv fuer Al-Nassr",
    },
    {
        "text": "Wird es 2025 einen dritten Weltkrieg geben?",
        "expected_direction": "low",
        "reason": "Katastrophisches Ereignis mit sehr kleiner Basisrate",
    },
    {
        "text": "Wird Bitcoin bis Ende 2025 ueber 50000 USD gehandelt?",
        "expected_direction": "high",
        "reason": "BTC stand 2025 deutlich ueber 50k",
    },
    {
        "text": "Wird die deutsche Wirtschaft 2025 schrumpfen?",
        "expected_direction": "open",
        "reason": "Genuiin ungewiss; gemischte Signale",
    },
    {
        "text": "Wird Donald Trump 2025 US-Praesident sein?",
        "expected_direction": "high",
        "reason": "Bereits bestaedigtes Ergebnis",
    },
    {
        "text": "Wird die Erde 2025 von einem Asteroiden getroffen?",
        "expected_direction": "low",
        "reason": "Astronomisch bekannt: nahezu null",
    },
]


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    question: str
    expected_direction: str
    probability: "float | None" = None
    confidence: "float | None" = None
    claim_count: int = 0
    pro_count: int = 0
    contra_count: int = 0
    latency_s: float = 0.0
    passed: bool = False
    error: "str | None" = None
    diagnostics: "dict[str, Any]" = field(default_factory=dict)

    @property
    def direction_ok(self) -> bool:
        if self.probability is None:
            return False
        if self.expected_direction == "high":
            return self.probability >= 0.55
        if self.expected_direction == "low":
            return self.probability <= 0.45
        return True

    @property
    def is_50pct_biased(self) -> bool:
        if self.probability is None:
            return False
        return P50_BAND[0] <= self.probability <= P50_BAND[1]


# ---------------------------------------------------------------------------
# HTTP-Hilfsfunktionen (Standard-Bibliothek)
# ---------------------------------------------------------------------------

def _http_post(url: str, payload: dict, params: dict = None) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _http_get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# ---------------------------------------------------------------------------
# Infrastruktur-Tests
# ---------------------------------------------------------------------------

def test_health(base: str) -> tuple[bool, str]:
    try:
        code, body = _http_get(f"{base}/health")
        data = json.loads(body)
        if code == 200 and data.get("status") == "ok":
            return True, "OK"
        return False, f"HTTP {code}"
    except Exception as exc:
        return False, str(exc)[:60]


def test_metrics(base: str) -> tuple[bool, str]:
    try:
        code, body = _http_get(f"{base}/metrics")
        if code == 200 and "forecast" in body:
            return True, "Prometheus-Metriken vorhanden"
        return False, f"HTTP {code}"
    except Exception as exc:
        return False, str(exc)[:60]


def test_404(base: str) -> tuple[bool, str]:
    try:
        code, _ = _http_get(f"{base}/questions/00000000-0000-0000-0000-000000000000")
        if code == 404:
            return True, "404 korrekt"
        return False, f"Erwartet 404, got {code}"
    except Exception as exc:
        return False, str(exc)[:60]


# ---------------------------------------------------------------------------
# Forecast-Test
# ---------------------------------------------------------------------------

def run_forecast_test(
    base: str,
    question_cfg: dict,
    language: str = "de",
    verbose: bool = False,
) -> TestResult:
    q_text    = question_cfg["text"]
    direction = question_cfg["expected_direction"]
    result    = TestResult(question=q_text, expected_direction=direction)

    t0 = time.perf_counter()

    # 1. Frage anlegen
    try:
        created = _http_post(f"{base}/questions", {
            "title": q_text,
            "description": "",
            "category": "test",
            "region": "global",
            "resolve_at": "2026-12-31T23:59:59",
            "resolution_criteria": q_text,
            "resolution_source_policy": "public_news",
        })
        qid = created["id"]
    except Exception as exc:
        result.error = f"Create: {exc}"
        result.latency_s = time.perf_counter() - t0
        return result

    # 2. Forecast anfordern
    try:
        fc = _http_post(
            f"{base}/questions/{qid}/forecast",
            payload={},
            params={"language": language},
        )
    except Exception as exc:
        result.error = f"Forecast: {exc}"
        result.latency_s = time.perf_counter() - t0
        return result

    result.latency_s = time.perf_counter() - t0

    # 3. Werte extrahieren
    try:
        result.probability = float(fc.get("probability") or 0.5)
        result.confidence  = float(fc.get("confidence") or 0.0)
        claims_raw         = fc.get("claims") or {}
        all_claims = (
            claims_raw.get("pro", []) +
            claims_raw.get("contra", []) +
            claims_raw.get("uncertainties", [])
        )
        result.claim_count  = len(all_claims)
        result.pro_count    = len(claims_raw.get("pro", []))
        result.contra_count = len(claims_raw.get("contra", []))
        result.diagnostics  = fc.get("diagnostics") or {}
    except Exception as exc:
        result.error = f"Parse: {exc}"
        return result

    if verbose:
        diag = result.diagnostics
        print(f"         prior={diag.get('probability_diagnostics', {}).get('prior_probability', '?')} "
              f"evidence_strength={diag.get('probability_diagnostics', {}).get('evidence_strength', '?')} "
              f"method={diag.get('probability_diagnostics', {}).get('method', '?')}")

    result.passed = result.direction_ok
    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def _pct(v: "float | None") -> str:
    return f"{v*100:.1f}%" if v is not None else "---"


def _ok(ok: bool) -> str:
    return f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"


def print_report(results: list, infra: list) -> int:
    sep = "=" * 72
    print(f"\n{BOLD}{sep}{RESET}")
    print(f"{BOLD}  4CPA Prognostic Engine  –  Reliability Report{RESET}")
    print(f"{sep}")

    # Infrastruktur
    print(f"\n{CYAN}INFRASTRUKTUR{RESET}")
    for name, ok, msg in infra:
        print(f"  [{_ok(ok)}]  {name:<30} {msg}")

    # Forecasts
    print(f"\n{CYAN}FORECAST-TESTS{RESET}")
    header = f"  {'#':<3} {'Frage':<47} {'Prob':>7} {'Claims':>6} {'Zeit':>7}  Ergebnis"
    print(header)
    print(f"  {'-'*72}")

    n_pass = n_fail = n_50bias = 0
    for i, r in enumerate(results, 1):
        q_short   = r.question[:45] + ".." if len(r.question) > 47 else r.question
        prob_str  = _pct(r.probability)
        time_str  = f"{r.latency_s:.1f}s"
        bias_flag = f" {YELLOW}[~50%]{RESET}" if r.is_50pct_biased else ""
        err_str   = f" {RED}{r.error[:35]}{RESET}" if r.error else ""

        if r.error:
            status = f"{RED}ERROR{RESET}"
            n_fail += 1
        elif r.passed:
            status = f"{GREEN}PASS{RESET}"
            n_pass += 1
        else:
            status = f"{RED}FALSCH{RESET}"
            n_fail += 1

        if r.is_50pct_biased:
            n_50bias += 1

        print(f"  {i:<3} {q_short:<47} {prob_str:>7} {r.claim_count:>6} {time_str:>7}  {status}{bias_flag}{err_str}")

    # 50%-Bias-Analyse
    total      = len(results)
    bias_share = n_50bias / max(1, total)
    bias_ok    = bias_share <= P50_MAX_SHARE

    print(f"\n{CYAN}50%-BIAS-ANALYSE{RESET}")
    print(f"  Ergebnisse im Band {P50_BAND[0]*100:.0f}–{P50_BAND[1]*100:.0f}%:  {n_50bias}/{total}  ({bias_share*100:.0f}%)")
    print(f"  Schwellwert:  max. {P50_MAX_SHARE*100:.0f}% zulaessig")
    print(f"  Bewertung:    [{_ok(bias_ok)}]{'  ZU VIELE ~50%-ERGEBNISSE' if not bias_ok else ''}")

    # Latenz
    latencies = [r.latency_s for r in results if not r.error]
    if latencies:
        print(f"\n{CYAN}LATENZ{RESET}")
        print(f"  Durchschnitt: {sum(latencies)/len(latencies):.1f}s   Max: {max(latencies):.1f}s")

    # Zusammenfassung
    infra_ok = all(ok for _, ok, _ in infra)
    all_ok   = n_fail == 0 and infra_ok and bias_ok
    result_str = f"{GREEN}GESAMTERGEBNIS: PASS{RESET}" if all_ok else f"{RED}GESAMTERGEBNIS: FAIL{RESET}"
    print(f"\n{BOLD}  {result_str}{RESET}  ({n_pass}/{total} Forecasts korrekt)")
    print(f"{sep}\n")
    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="4CPA Reliability Test")
    parser.add_argument("--local",   action="store_true", help="localhost:8000")
    parser.add_argument("--verbose", action="store_true", help="Diagnostics ausgeben")
    parser.add_argument("--quick",   action="store_true", help="Nur 3 Fragen")
    parser.add_argument("--lang",    default="de", help="Sprache (de/en/fr/it/es)")
    args = parser.parse_args()

    base = LOCAL_BASE if args.local else LIVE_BASE
    tag  = "local" if args.local else "live"
    print(f"Ziel: {CYAN}{tag} ({base}){RESET}")

    questions = TEST_QUESTIONS[:3] if args.quick else TEST_QUESTIONS

    # Infrastruktur-Checks
    print("Infrastruktur...")
    infra = [
        ("Health /health",          *test_health(base)),
        ("Metrics /metrics",        *test_metrics(base)),
        ("404-Handling",            *test_404(base)),
    ]

    # Forecast-Tests
    results: list[TestResult] = []
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['text'][:65]}...")
        r = run_forecast_test(base, q, language=args.lang, verbose=args.verbose)
        results.append(r)
        status = "PASS" if r.passed else ("ERROR" if r.error else "FALSCH")
        print(f"         Prob={_pct(r.probability)}  {r.latency_s:.1f}s  [{status}]")

    return print_report(results, infra)


if __name__ == "__main__":
    sys.exit(main())
