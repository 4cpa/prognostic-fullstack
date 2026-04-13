# 4cpa Prognostic

AI-gestütztes Forecast-System zur probabilistischen Beantwortung von Prognosefragen.  
Das System recherchiert Quellen, extrahiert Claims und berechnet Wahrscheinlichkeiten via Bayesianischer Log-Odds-Methode – unterstützt durch Gemini 2.0 Flash.

---

## Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Architektur](#architektur)
3. [Verzeichnisstruktur](#verzeichnisstruktur)
4. [Datenmodell](#datenmodell)
5. [Backend – API-Referenz](#backend--api-referenz)
6. [Forecast-Engine](#forecast-engine)
7. [LLM-Integration (Gemini)](#llm-integration-gemini)
8. [Backtesting & Kalibrierung](#backtesting--kalibrierung)
9. [Frontend](#frontend)
10. [Testing](#testing)
11. [Monitoring](#monitoring)
12. [Versioning](#versioning)
13. [Lokale Entwicklung](#lokale-entwicklung)
14. [Deployment](#deployment)
15. [Konfiguration & Umgebungsvariablen](#konfiguration--umgebungsvariablen)

---

## Überblick

**4cpa Prognostic** beantwortet Prognosefragen in natürlicher Sprache mit einer kalibrierten Wahrscheinlichkeit und einer strukturierten Erklärung. Der Ablauf je Anfrage:

```
Frage → Quellenrecherche → Claim-Extraktion → Scoring → Bayesian-Aggregation → Kalibrierung → Erklärung (LLM)
```

Sprachen: Deutsch, Englisch, Französisch, Italienisch, Spanisch.

---

## Architektur

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx (Reverse Proxy)               │
└────────────────┬──────────────────────┬─────────────────┘
                 │                      │
         :3000   ▼              :8000   ▼
    ┌──────────────────┐   ┌──────────────────────┐
    │  Next.js Frontend│   │  FastAPI Backend      │
    │  (TypeScript)    │   │  (Python)             │
    └──────────────────┘   └────────┬─────────────┘
                                    │
                           :5432    ▼
                      ┌──────────────────────┐
                      │  PostgreSQL 15        │
                      │  (prognosticdb)       │
                      └──────────────────────┘
```

Alle Services laufen als Docker-Container und kommunizieren über ein internes Docker-Netzwerk.

---

## Verzeichnisstruktur

```
prognostic-fullstack/
├── app/                        # FastAPI-Backend
│   ├── main.py                 # App-Einstiegspunkt, Middleware, Router
│   ├── api/
│   │   ├── routes_questions.py # CRUD für Fragen & Evidence
│   │   ├── routes_forecasts.py # Forecast-Erzeugung & -Abruf
│   │   └── routes_backtesting.py # Backtesting & Kalibrierungsdaten
│   ├── core/
│   │   ├── config.py           # Settings (DATABASE_URL, GEMINI_API_KEY)
│   │   ├── db.py               # SQLModel Session-Factory
│   │   ├── forecast_engine.py  # Zentrale Forecast-Logik
│   │   ├── llm_service.py      # Gemini-Integration
│   │   ├── claim_extraction.py # Regelbasierte + LLM-Claim-Extraktion
│   │   ├── claim_scoring.py    # Claim-Gewichtung & -Aggregation
│   │   ├── source_research.py  # Web-Quellensuche
│   │   ├── calibration.py      # Kalibrierungsalgorithmen
│   │   ├── calibration_service.py # Kalibrierungs-Datenzugriff
│   │   ├── hashing.py          # Input-Hashing für Deduplizierung
│   │   └── logger.py           # Strukturiertes Logging
│   └── models/
│       ├── question.py         # Question, QuestionCreate, QuestionRead
│       ├── forecast.py         # Forecast, ForecastRead
│       ├── evidence.py         # EvidenceItem
│       ├── forecast_claim.py   # ForecastClaim
│       ├── forecast_source.py  # ForecastSource
│       ├── source.py           # Source
│       └── links.py            # Hilfsmodelle
├── frontend/                   # Next.js-Frontend
│   ├── app/
│   │   ├── page.tsx            # Startseite mit Eingabeformular
│   │   ├── HomeForm.tsx        # Formular-Komponente
│   │   ├── SearchForm.tsx      # Suchkomponente
│   │   ├── layout.tsx          # Root-Layout
│   │   └── forecast/           # Forecast-Ergebnisseite
│   └── src/lib/api/            # API-Client-Funktionen
├── alembic/                    # Datenbankmigrationen
│   └── versions/               # Migrationsdateien
├── tests/                      # Test-Suite
├── docker-compose.yml          # Multi-Service-Orchestrierung
├── Dockerfile                  # Backend-Image
├── requirements.txt            # Python-Abhängigkeiten
├── DEPLOYMENT.md               # Deployment-Prozess
└── README.md                   # Diese Datei
```

---

## Datenmodell

### Question

| Feld                     | Typ          | Beschreibung                              |
|--------------------------|--------------|-------------------------------------------|
| `id`                     | UUID (PK)    | Eindeutige ID                             |
| `title`                  | str          | Kurztitel der Frage                       |
| `description`            | str?         | Ausführliche Beschreibung                 |
| `category`               | str?         | Themenbereich (z. B. Politik, Wirtschaft) |
| `region` / `country`     | str?         | Geografischer Bezug                       |
| `resolve_at`             | datetime?    | Geplanter Auflösungszeitpunkt             |
| `resolution_criteria`    | str?         | Kriterien für Ja/Nein-Entscheidung        |
| `status`                 | enum         | `open`, `resolved_yes`, `resolved_no`, `void` |
| `resolved_at`            | datetime?    | Tatsächliches Auflösungsdatum             |
| `outcome`                | str?         | `yes` / `no` / `void`                    |

### Forecast

| Feld                        | Typ      | Beschreibung                                  |
|-----------------------------|----------|-----------------------------------------------|
| `id`                        | UUID (PK)| Eindeutige ID                                 |
| `question_id`               | FK       | Verknüpfte Frage                              |
| `probability`               | float    | Finale Wahrscheinlichkeit [0, 1]              |
| `raw_probability`           | float?   | Rohwert vor Kalibrierung                      |
| `calibrated_probability`    | float?   | Kalibrierter Wert                             |
| `confidence`                | float?   | Konfidenz des Forecasts [0, 1]                |
| `method`                    | str      | Algorithmus (z. B. `bayes_logodds_v1`)        |
| `method_version`            | str      | Versionsstring (z. B. `v0.1.0`)               |
| `explanation_md`            | str      | Markdown-Erklärung (LLM-generiert)            |
| `summary`                   | str?     | Kurzzusammenfassung                           |
| `direct_answer`             | str?     | Ja/Nein-Direktantwort                         |
| `answer_label`              | str?     | Menschenlesbares Label (z. B. „Wahrscheinlich") |
| `answer_confidence_band`    | str?     | Bandbreite (z. B. „60–70 %")                  |
| `sources`                   | JSONB?   | Recherchierte Quellen                         |
| `claims`                    | JSONB?   | Extrahierte Claims                            |
| `top_pro_claims`            | JSONB?   | Stärkste Pro-Argumente                        |
| `top_contra_claims`         | JSONB?   | Stärkste Contra-Argumente                     |
| `top_uncertainties`         | JSONB?   | Wichtigste Unsicherheiten                     |
| `diagnostics`               | JSONB?   | Engine-Diagnosedaten                          |
| `inputs_hash`               | str      | SHA-256 der Eingaben (Deduplizierung)         |

### EvidenceItem

Manuelle Evidenz, die einer Frage zugeordnet wird (z. B. Experteneinschätzungen).

| Feld             | Typ   | Beschreibung                              |
|------------------|-------|-------------------------------------------|
| `indicator_type` | str   | Art der Evidenz                           |
| `direction`      | str   | `pro` / `contra` / `uncertainty`          |
| `weight`         | float | Gewichtung [0, 1]                         |
| `note`           | str?  | Freitextnotiz                             |

---

## Backend – API-Referenz

Basis-URL: `http://localhost:8000`  
Interaktive Dokumentation: `http://localhost:8000/docs`

### Questions

| Methode | Pfad                              | Beschreibung                        |
|---------|-----------------------------------|-------------------------------------|
| POST    | `/questions`                      | Neue Frage erstellen                |
| GET     | `/questions/{id}`                 | Frage abrufen                       |
| POST    | `/questions/{id}/evidence`        | Manuelle Evidenz hinzufügen         |
| GET     | `/questions/{id}/evidence`        | Evidenzliste abrufen                |
| POST    | `/questions/{id}/resolve`         | Frage auflösen (`yes`/`no`/`void`)  |

### Forecasts

| Methode | Pfad                                    | Beschreibung                              |
|---------|-----------------------------------------|-------------------------------------------|
| POST    | `/questions/{id}/forecast`              | Neuen Forecast erzeugen                   |
| GET     | `/questions/{id}/forecast/latest`       | Letzten Forecast (Kurzform) abrufen       |
| GET     | `/questions/{id}/forecast/latest/full`  | Letzten Forecast (Vollform) abrufen       |
| POST    | `/questions/{id}/forecast/recompute`    | Letzten Forecast neu berechnen            |

Query-Parameter für Forecast-Endpunkte:
- `language` – Antwortsprache: `de` (Standard), `en`, `fr`, `it`, `es`
- `method_version` – Versionsstring, Standard: `v0.1.0`

### Backtesting

| Methode | Pfad                          | Beschreibung                               |
|---------|-------------------------------|---------------------------------------------|
| GET     | `/backtesting/summary`        | Aggregierte Backtesting-Metriken           |
| GET     | `/backtesting/calibration`    | Kalibrierungstabellen (global + Kategorie) |
| GET     | `/backtesting/runtime`        | Laufzeit-Kalibrierungspayload              |

Query-Parameter: `num_bins` (2–20, Standard 10), `min_bin_count` (1–100, Standard 3)

### Health

```
GET /health  →  {"status": "ok"}
```

---

## Forecast-Engine

Die Engine (`app/core/forecast_engine.py`) verarbeitet eine Frage in folgenden Schritten:

1. **Quellenrecherche** (`source_research.py`)  
   Gemini generiert 4 gezielte Suchanfragen; Ergebnisse werden nach Aktualität gewichtet (`freshness_score`).

2. **Claim-Extraktion** (`claim_extraction.py`)  
   Pro Quelle werden Claims als `pro`, `contra`, `uncertainty` oder `background` klassifiziert. LLM-basiert mit regelbasiertem Fallback.

3. **Claim-Scoring** (`claim_scoring.py`)  
   Claims erhalten Scores basierend auf `claim_confidence` × `time_relevance` × Quelltyp-Gewicht.

4. **Bayesian Log-Odds-Aggregation**  
   Ausgehend von einem Prior (50 %) werden Pro- und Contra-Scores via Log-Odds addiert.  
   Formel: `log_odds = log(p / (1-p))`, dann Update pro Claim, abschließend Rücktransformation.

5. **Kalibrierung** (`calibration_service.py`)  
   Historische Forecast-Güte wird aus aufgelösten Fragen berechnet und auf den Rohwert angewendet.  
   Endwahrscheinlichkeit wird auf [0,05; 0,95] begrenzt.

6. **Erklärungsgenerierung** (`llm_service.py`)  
   Gemini schreibt eine 3–4-Absätze-Markdown-Erklärung in der gewünschten Sprache.

**EngineConfig-Standardwerte:**

| Parameter             | Wert |
|-----------------------|------|
| `max_sources`         | 8    |
| `max_claims`          | 20   |
| `top_claims_per_bucket` | 3  |
| `prior_probability`   | 0.50 |
| `min_confidence`      | 0.05 |
| `max_confidence`      | 0.95 |

---

## LLM-Integration (Gemini)

Modul: `app/core/llm_service.py`  
Modell: `gemini-2.0-flash`

Drei Funktionen:

| Funktion                       | Aufgabe                                    | Fallback                    |
|--------------------------------|--------------------------------------------|-----------------------------|
| `generate_search_queries()`    | 4 Suchanfragen für Quellenrecherche        | Leere Liste                 |
| `extract_claims_with_llm()`    | Claim-Extraktion aus Quelltext             | Regelbasierte Extraktion    |
| `generate_forecast_explanation()` | Markdown-Erklärung in Zielsprache       | Template-basierter Text     |

Wenn `GEMINI_API_KEY` nicht gesetzt ist oder ein Fehler auftritt, greifen alle Funktionen auf deterministische Fallbacks zurück – das System ist damit auch ohne API-Key funktionsfähig.

---

## Backtesting & Kalibrierung

Das System lernt aus aufgelösten Fragen:

- **Brier Score**: Mittlerer quadratischer Fehler zwischen Forecast-Wahrscheinlichkeit und tatsächlichem Ausgang.
- **Kalibrierungskurve**: Vergleich vorhergesagter vs. beobachteter Häufigkeiten in Wahrscheinlichkeitsbins.
- **Laufzeit-Kalibrierung**: Bin-spezifische Korrekturfaktoren, die auf neue Forecasts angewendet werden.

Kalibrierungsdaten sind über `/backtesting/*` abrufbar und werden nach jeder Frageauflösung automatisch aktualisiert.

---

## Frontend

Technologie-Stack: **Next.js 14+ (App Router)**, TypeScript, Tailwind CSS

**Seitenstruktur:**

| Route            | Komponente        | Beschreibung                              |
|------------------|-------------------|-------------------------------------------|
| `/`              | `HomeForm.tsx`    | Eingabeformular für Prognosefragen        |
| `/forecast/[id]` | Forecast-Seite    | Ergebnisanzeige: Wahrscheinlichkeit, Claims, Quellen, Erklärung |

Das Frontend kommuniziert direkt mit dem Backend über die REST-API (`/src/lib/api/`).

---

## Testing

### Struktur

```
tests/
├── conftest.py              # Fixtures: SQLite-In-Memory-DB, TestClient
├── unit/
│   └── test_claim_scoring.py
└── integration/
    ├── test_health.py        # /health, /metrics
    └── test_questions_api.py # CRUD, Evidence, Auflösung
```

### Tests ausführen

```bash
# Nur Unit-Tests (kein Docker nötig)
pytest tests/unit -m unit

# Alle Tests (braucht laufende DB oder Docker)
pytest

# Mit Log-Output in logs/test.log
pytest --log-file=logs/test.log
```

### Log-Output

`pytest.ini` konfiguriert automatisch:
- **Konsole**: `INFO`-Level, lesbar formatiert
- **`logs/test.log`**: `DEBUG`-Level, vollständig mit Datei/Zeile
- **JUnit-XML**: `logs/junit-unit.xml` / `logs/junit-integration.xml` für CI

### CI (GitHub Actions)

`.github/workflows/ci.yml` läuft bei jedem Push auf `main` und bei Pull Requests:
- Startet PostgreSQL als Service-Container
- Führt Unit- und Integrationstests separat aus
- Lädt `logs/test.log` + JUnit-XMLs als Artifact hoch (14 Tage Aufbewahrung)
- Zeigt Testergebnisse direkt im PR als Check an

---

## Monitoring

### Systemmetriken: Netdata

Netdata läuft bereits auf dem Server und überwacht CPU, RAM, Disk, Network.

### Endpoint-Monitoring: Uptime Kuma

Uptime Kuma läuft als Docker-Container und überwacht HTTP-Endpunkte mit Alerting.

```
http://localhost:3001   (lokal, via Nginx reverse-proxied auf externes Port)
```

Nach dem ersten Start einrichten:
1. Account anlegen unter `http://<server>/uptime`
2. Monitor hinzufügen → **HTTP(s)** → URL: `http://backend:8000/health`
3. Notifications konfigurieren (E-Mail, Telegram, Slack, etc.)

### Applikationsmetriken: Prometheus

Das Backend exposes `/metrics` im Prometheus-Format:

```
GET http://localhost:8000/metrics
```

Enthält: HTTP-Request-Count, Latenz-Histogramm, Status-Codes — aufgeschlüsselt nach Route.

Für eine vollständige Grafana-Integration kann Prometheus als weiterer Docker-Service ergänzt werden (optionaler nächster Schritt).

---

## Versioning

Das Projekt verwendet [Semantic Versioning](https://semver.org/lang/de/): `MAJOR.MINOR.PATCH`

### VERSION-Datei

Die aktuelle Version steht in `VERSION`. Der Release-Workflow (`release.yml`) erstellt automatisch einen Git-Tag und ein GitHub-Release, sobald `VERSION` auf `main` geändert wird.

### Workflow für ein neues Release

```bash
# 1. CHANGELOG pflegen (optional: Script nutzen)
./scripts/changelog-entry.sh "Added" "Neue Feature-Beschreibung"

# 2. Version erhöhen + CHANGELOG automatisch aktualisieren
./scripts/bump-version.sh minor   # oder: patch / major

# 3. Committen und pushen → GitHub Actions erstellt Tag + Release
git add VERSION CHANGELOG.md
git commit -m "chore: release v0.5.0"
git push
```

### Scripts

| Script | Zweck |
|--------|-------|
| `scripts/bump-version.sh <patch\|minor\|major>` | VERSION erhöhen, CHANGELOG aktualisieren |
| `scripts/changelog-entry.sh <Typ> <Text>` | Eintrag in [Unreleased] hinzufügen |
| `scripts/export-openapi.sh [BASE_URL]` | OpenAPI-Schema als `docs/openapi.json` exportieren |

---

## Lokale Entwicklung

### Voraussetzungen

- Docker & Docker Compose
- Node.js 18+ (für Frontend-Entwicklung ohne Docker)
- Python 3.11+ (für Backend-Entwicklung ohne Docker)

### Mit Docker starten

```bash
# .env-Datei anlegen
cp .env.example .env
# POSTGRES_PASSWORD und GEMINI_API_KEY eintragen

# Alle Services starten
docker compose up --build

# Nur Backend neu bauen
docker compose up --build backend
```

Dienste nach dem Start:

| Service  | URL                     |
|----------|-------------------------|
| Frontend | http://localhost:3000   |
| Backend  | http://localhost:8000   |
| API-Docs | http://localhost:8000/docs |

### Datenbankmigrationen

```bash
# Neue Migration erstellen
alembic revision --autogenerate -m "beschreibung"

# Migrationen anwenden
alembic upgrade head

# Im Container ausführen
docker compose exec backend alembic upgrade head
```

### Tests ausführen

```bash
cd prognostic-fullstack
pytest tests/
```

---

## Deployment

Vollständige Deployment-Dokumentation: [DEPLOYMENT.md](./DEPLOYMENT.md)

**Kurzüberblick:**

- Deployment-Strategie: **Immutable Server** via GitHub Actions
- Produktionsserver: `transivroom` unter `/srv/4cpa/prognostic-fullstack`
- Trigger: Push/Merge auf `main`-Branch
- Direktes Editieren auf dem Produktionsserver ist **verboten**

```
lokale Änderung → git push → PR → merge main → GitHub Actions → SSH-Deploy
```

---

## Konfiguration & Umgebungsvariablen

| Variable           | Pflicht | Standardwert                                        | Beschreibung                    |
|--------------------|---------|-----------------------------------------------------|---------------------------------|
| `DATABASE_URL`     | ja      | `postgresql+psycopg2://postgres:postgres@localhost:5432/prognostic` | PostgreSQL-Verbindung |
| `POSTGRES_PASSWORD`| ja      | –                                                   | Datenbankpasswort (Docker)      |
| `GEMINI_API_KEY`   | nein    | `""`                                                | Google Gemini API-Schlüssel; ohne Key läuft das System im Fallback-Modus |

---

## Technologie-Stack

| Schicht     | Technologie                            |
|-------------|----------------------------------------|
| Backend     | Python 3.11, FastAPI 0.110, SQLModel   |
| Datenbank   | PostgreSQL 15                          |
| ORM/Migration | SQLAlchemy 2, Alembic               |
| LLM         | Google Gemini 2.0 Flash                |
| Frontend    | Next.js 14, TypeScript, Tailwind CSS   |
| Container   | Docker, Docker Compose                 |
| CI/CD       | GitHub Actions                         |

---

*Transivroom Division 2026*
