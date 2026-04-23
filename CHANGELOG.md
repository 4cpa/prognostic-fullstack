# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.  
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).  
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

---

## [Unreleased]

---

## [1.0.2] – 2026-04-23

### Hinzugefügt
- Twint-Spende-Button im Footer neben Ko-fi (persönlicher Zahlungslink)

### Geändert
- Twint-Button: Gelb/Schwarz-Farbschema (`#FFCC00`/`#000`), T-Lettermark-Icon, `font-weight: 800`
- GitHub-Button: präzises Octocat-SVG (offizieller GitHub-Pfad)
- Transivroom-Button: `whiteSpace: nowrap` und angepasstes Padding – Text wird nicht mehr abgeschnitten

---

## [1.0.1] – 2026-04-14

### Hinzugefügt
- Vollständige UI-Internationalisierung (i18n): Sprachauswahl übersetzt die gesamte Startseite (Tagline, Formular-Labels, Placeholder, Fehlermeldungen, „Wie es funktioniert") in DE, EN, FR, IT, ES
- `LanguageContext` (`language-context.tsx`): geteilter Client-State zwischen `HomeForm` und `FooterContent`
- `FooterContent.tsx`: Footer-Disclaimer und Lizenztext werden mit der Sprachauswahl übersetzt
- Ko-fi-Spende-Button im Footer (mehrsprachig, ID `E1E11XU5UD`)
- Logo (`icon.png`, transparent) neben dem Seitentitel – 92px, vertikal zentriert zu beiden Titelzeilen
- Indigo→Sky-Farbverlauf als 4px-Balken am oberen Seitenrand (`#6366f1` → `#0ea5e9`)

### Geändert
- Footer einheitlich dunkel (`#0f172a`) auf allen Plattformen (iOS und Desktop)
- Layout: `<body>` mit `flex-col min-h-dvh bg-slate-50`; `<main>` mit `flex-1` – Footer klebt stets am unteren Rand
- `globals.css`: Dark-Mode-Hintergrund-Override entfernt – verhindert schwarzen Footer auf iOS
- Desktop-Layout: `py-12 sm:py-16` für bessere vertikale Proportionen auf grossen Screens
- Logo-Hintergrund in `icon.png` entfernt (transparent, via ImageMagick)

### Behoben (CI/CD)
- `pytestmark = pytest.mark.unit` in `tests/unit/test_claim_scoring.py` ergänzt
- `pythonpath = .` in `pytest.ini` – `app`-Modul in GitHub Actions importierbar
- `JSONB` → `JSON` in `app/models/forecast.py` – SQLite-kompatibel für Integrationstests
- `docker.yml`: Backend-Context von `./backend` auf `.` korrigiert
- `deploy.yml`: Username `deploy` → `transiv`, korrekter VPS-Pfad

---

## [0.4.0] – 2026-04-13

### Hinzugefügt
- Prometheus-Metriken-Endpunkt (`/metrics`) via `prometheus-fastapi-instrumentator`
- Uptime Kuma Service in `docker-compose.yml` (Endpoint-Monitoring & Alerting)
- `pytest.ini` mit strukturiertem Log-Output in `logs/test.log`
- `tests/conftest.py` mit SQLite-In-Memory-Fixtures für schnelle Integrationstests
- Integrationstests: Health-Endpunkt, Questions-CRUD, Evidence, Auflösung
- `VERSION`-Datei für Semantic Versioning
- `CHANGELOG.md` (diese Datei)
- GitHub Actions CI-Workflow mit Testlauf und Log-Artifact-Upload
- GitHub Actions Release-Workflow: Auto-Tag bei `VERSION`-Änderung
- Vollständige Projektdokumentation (`README.md`)

---

## [0.3.0] – 2026-04-12

### Hinzugefügt
- Footer mit "Transivroom Division 2026" und mailto-Link

### Geändert
- Deployment-Workflow: Verwende `deploy`-User statt `transiv`

---

## [0.2.0] – 2026-04-10

### Hinzugefügt
- Gemini LLM als primäre KI-Engine (ersetzt vorherigen LLM-Anbieter)
- Alle Themen geöffnet (kein Topic-Filter mehr)
- Universelle Link-Vorschau für Quellen

### Hinzugefügt
- Strukturiertes JSON-Logging (`app/core/logger.py`)
- Geführte API-Key-Einrichtung bei Konfigurationsfehlern

---

## [0.1.0] – 2026-03-15

### Hinzugefügt
- Initiales Release
- FastAPI-Backend mit Questions-, Forecasts- und Backtesting-Router
- Bayesianische Log-Odds Forecast-Engine
- Quellenrecherche und Claim-Extraktion
- Kalibrierungssystem aus historischen Forecasts
- Next.js-Frontend mit Eingabeformular und Ergebnisseite
- PostgreSQL-Datenbankmodell mit Alembic-Migrationen
- Docker-Compose-Setup
- GitHub Actions für Build und Deployment

---

[Unreleased]: https://github.com/4cpa/prognostic-fullstack/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/4cpa/prognostic-fullstack/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/4cpa/prognostic-fullstack/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/4cpa/prognostic-fullstack/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/4cpa/prognostic-fullstack/releases/tag/v0.1.0
