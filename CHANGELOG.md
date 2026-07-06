# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.  
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).  
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

---

## [Unreleased]

---

## [1.1.4] – 2026-07-06

### Geändert
- Forecast-Berechnung beschleunigt: Die LLM-Basisratenschätzung läuft jetzt parallel zur Quellenrecherche, und die beiden abschließenden LLM-Aufrufe (Erklärung + Direktantwort) laufen ebenfalls parallel statt nacheinander — beide Paare sind voneinander unabhängig, sodass ein kompletter LLM-Roundtrip pro Forecast eingespart wird.
- Sichtbares Fortschritts-Feedback beim Warten auf einen Forecast: Statt eines kaum sichtbaren, ausgegrauten Mini-Spinners zeigt das Formular jetzt eine deutlich sichtbare, drehende Uhr mit Live-Statustext ("Quellen werden durchsucht…" → "Belege werden bewertet…" → "Erklärung wird formuliert…"), gespeist durch einen neuen Backend-Endpoint (`GET /questions/{id}/forecast/progress`), der den echten Fortschritt der laufenden Berechnung zurückgibt.

### Behoben
- `_fetch_candidates()` (Quellenrecherche) wartete beim Verlassen des `ThreadPoolExecutor`-Blocks trotz abgelaufenem 17s-Timeout weiter auf alle bereits gestarteten Threads (`shutdown(wait=True)` im impliziten `with`-Exit) und liess bei Timeout sogar eine unbehandelte Exception durchschlagen, statt mit den bis dahin gesammelten Treffern weiterzumachen. Der Timeout wird jetzt tatsächlich durchgesetzt (`shutdown(wait=False, cancel_futures=True)`), und ein Timeout führt zu einem Teilergebnis statt zu einem Fehler.

---

## [1.1.3] – 2026-07-06

### Behoben
- Netdata versuchte täglich, sich über den `go.d`-Postgres-Collector mit dem Standard-User `netdata` an der App-Postgres-Instanz anzumelden — diese Rolle existiert dort nicht (nur `prognostic`), was seit 2026-06-24 zu einem täglichen `password authentication failed`-Eintrag im Postgres-Log führte. Collector über `/etc/netdata/go.d.conf` (`postgres: no`) deaktiviert; System- und App-Metriken (Netdata bzw. Prometheus `/metrics`) sind davon unberührt.

---

## [1.1.2] – 2026-07-06

### Behoben
- Integrationstests liefen nie erfolgreich durch: `tests/conftest.py` rief `SQLModel.metadata.create_all()` auf, bevor die App-Modelle importiert waren, wodurch die SQLite-Test-DB ohne Tabellen blieb ("no such table: questions"). Dieser Fehler war bisher verdeckt, weil ein vorheriger Unit-Test-Fehler (siehe 1.1.1) die CI-Pipeline schon vorher gestoppt hat.
- `EvidenceItem.direction` (manuelle Evidenz-Einträge) war als `int` (-1/+1) modelliert, während README und API-Konsumenten den dokumentierten Vertrag `str` (`pro`/`contra`/`uncertainty`) erwarten — jeder spezifikationskonforme Aufruf von `POST /questions/{id}/evidence` schlug mit 422 fehl. Model auf `str` korrigiert, inkl. Alembic-Migration für die bestehende Postgres-Spalte (`direction`: `INTEGER` → `VARCHAR`, vorhandene Werte `1`/`-1` werden zu `pro`/`contra` migriert). **Migration muss nach dem Deploy manuell mit `alembic upgrade head` auf dem Server angewendet werden** (siehe DEPLOYMENT.md).

---

## [1.1.1] – 2026-07-06

### Behoben
- Scoring-Bug: Der „Directional-Imbalance-Bonus" (bis zu +20% bei einseitiger Pro/Contra-Evidenz) konnte die Uncertainty-Dämpfung überkompensieren, wodurch Unsicherheits-Claims das `net_signal` paradoxerweise erhöhten statt zu senken (`test_uncertainty_claims_reduce_effective_net_signal`, seit 2026-05-14 durchgehend rot). Der Bonus greift jetzt nur noch, wenn keine nennenswerte Unsicherheit vorliegt — bei vorhandener Unsicherheit hat die Vorsichts-Dämpfung Vorrang.

---

## [1.1.0] – 2026-07-06

### Hinzugefügt
- Cloudflare als Hybrid-Proxy vor die Produktionsumgebung geschaltet: DNS-Verwaltung über Cloudflare-Nameserver, SSL/TLS-Modus „Full (strict)", WAF/DDoS-Schutz auf Netzwerkebene
- Automatisierte wöchentliche Aktualisierung der Cloudflare-IP-Ranges via Cronjobs auf dem VPS — sowohl für die Nginx-`real_ip`-Konfiguration als auch für die Hetzner-Cloud-Firewall-Regeln (über die Hetzner-API, mit eingebauter Sicherung gegen versehentliches Entfernen der SSH-Regel)
- KI-Disclaimer-Banner auf der Forecast-Detailseite

### Geändert
- Origin-Firewall (Hetzner Cloud) lässt eingehenden Traffic auf Port 80/443 nur noch von Cloudflare-IP-Ranges zu; die zuvor öffentlich erreichbaren Ports 3000 (Frontend) und 8000 (Backend) wurden komplett entfernt, da Nginx diese ohnehin nur intern proxyt und sie sonst Cloudflare und Nginx umgehen konnten
- Nginx: `real_ip`-Modul aktiviert, damit Access-Logs und das Netdata-Monitoring wieder die echten Besucher-IPs statt Cloudflare-Edge-IPs anzeigen
- KI-Disclaimer-Text wärmer und nuancierter formuliert (Variante 3)

### Behoben
- Rohe `SyntaxError`-Meldung wurde bei fehlerhaftem JSON-Parsing direkt an den User durchgereicht statt einer verständlichen Fehlermeldung
- Favicon-Darstellung in Safari: Next.js-Standard-Favicon durch 4cpa-Logo ersetzt, Cache-Refresh erzwungen (`?v=2`), zusätzliches `favicon.ico` in `app/` für höchste Next.js-Priorität ergänzt

---

## [1.0.7] – 2026-05-02

### Hinzugefügt
- Antwortseite: Zurück-Navigation zum Frageformular in der jeweiligen Sprache (de/en/fr/it/es) — dezenter Link oben (vor dem Titel) und prominenter CTA-Button unten (nach den Quellen)

---

## [1.0.6] – 2026-04-23

### Behoben
- Footer-Buttons (GitHub, TWINT, Transivroom) auf schmalen iOS-Screens zu klein für Text: Flex-Container der Button-Row um `flex-wrap: wrap` und `justify-content: center` ergänzt — Buttons mit `white-space: nowrap` wurden von der Flex-Logik schmaler als ihr Textinhalt gedrückt, da keine Zeile umbrechen konnte

---

## [1.0.5] – 2026-04-23

### Behoben
- Footer-Icons auf iOS definitiv unsichtbar: Alle inline `<svg>`-Elemente (E-Mail, GitHub, Ko-fi, TWINT) durch `<img src="/icons/xxx.svg">` ersetzt — gleicher Ansatz wie der funktionierende Transivroom-Button; SVG-Dateien mit fest codierten Farben in `/public/icons/` abgelegt

---

## [1.0.4] – 2026-04-23

### Behoben
- @4-Logo erscheint in Safari iOS (Verlaufsliste, Lesezeichen) nicht: `app/apple-icon.png` entfernt, das Next.js veranlasste einen zweiten `apple-touch-icon`-Link mit wechselnder Hash-URL zu generieren, der Safaras Cache-Lookup verhinderte – stattdessen expliziter `<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />` im `<head>`

---

## [1.0.3] – 2026-04-23

### Behoben
- Footer-Icons (GitHub, TWINT) wurden auf iOS (Safari, Chrome, Firefox, Vivaldi, Brave) nicht angezeigt
  - GitHub: ungültiges `clipRule="evenodd"` auf normalem `<path>` entfernt – WebKit verwarf dadurch die gesamte Pfad-Darstellung
  - TWINT: `fill="url(#id)"` SVG-Gradienten-Referenzen durch Festfarben (`#FF5500`, `#0292CD`) ersetzt – iOS WebKit löst Fragment-IDs in inline-SVGs als seitenrelative URLs auf, was in Next.js-Apps zum Renderingfehler führt

---

## [1.0.2] – 2026-04-23

### Hinzugefügt
- Twint-Spende-Button im Footer neben Ko-fi (persönlicher Zahlungslink)

### Geändert
- Twint-Button: offizielles TWINT-Logo-SVG von twint.ch (schwarzes Rounded-Rect, weisser Schriftzug, Hexagon-Icon mit Orange/Blau-Verlauf), 63×24px inline-SVG
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

[Unreleased]: https://github.com/4cpa/prognostic-fullstack/compare/v1.1.3...HEAD
[1.1.3]: https://github.com/4cpa/prognostic-fullstack/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/4cpa/prognostic-fullstack/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/4cpa/prognostic-fullstack/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/4cpa/prognostic-fullstack/compare/v1.0.0...v1.1.0
[0.4.0]: https://github.com/4cpa/prognostic-fullstack/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/4cpa/prognostic-fullstack/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/4cpa/prognostic-fullstack/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/4cpa/prognostic-fullstack/releases/tag/v0.1.0
