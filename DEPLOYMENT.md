# Deployment Guide – 4cpa Prognostic Fullstack

## Produktions-Deployment

Deployment-Strategie: **Git Pull + Docker Compose** via GitHub Actions SSH.

---

## Umgebungen

### Lokale Entwicklung
Maschine: `dispatch`  
Pfad: `/home/ops/prognostic-fullstack`

### Produktion (VPS)
Server: `transivroom` (`37.27.37.136`)  
User: `transiv`  
Pfad: `/home/transiv/prognostic-fullstack`  
Deployment: GitHub Actions → SSH → `git pull` + `docker compose up -d --build`

---

## GitHub Actions Workflows

| Workflow              | Trigger         | Aktion                                              |
|-----------------------|-----------------|-----------------------------------------------------|
| `CI – Tests`          | push `main`, PR | pytest Unit + Integration (Python 3.10 & 3.11)      |
| `Docker Build Check`  | push `main`, PR | Backend + Frontend Docker-Build (kein Push)          |
| `Deploy to Server`    | push `main`     | SSH-Deploy auf VPS                                   |

### Secrets (GitHub → Settings → Secrets → Actions)

| Secret            | Wert                        |
|-------------------|-----------------------------|
| `SERVER_HOST`     | `37.27.37.136`              |
| `SERVER_SSH_KEY`  | Privater SSH-Key für `transiv` |

---

## Deployment-Ablauf

```
lokale Änderung
  → git commit + git push
  → GitHub Actions (CI grün?)
  → deploy.yml: SSH → git pull → docker compose up -d --build frontend backend
```

Manuell (Fallback):
```bash
ssh transiv@37.27.37.136
cd /home/transiv/prognostic-fullstack
git pull
docker compose up -d --build frontend
```

---

## Services

| Service          | Port (intern) | Beschreibung                        |
|------------------|---------------|-------------------------------------|
| `frontend`       | 3000          | Next.js (hinter Nginx)              |
| `backend`        | 8000          | FastAPI                             |
| `postgres`       | 5432          | PostgreSQL 15                       |
| `uptime-kuma`    | 3001          | Endpoint-Monitoring                 |

---

## Datenbankmigrationen

Migrationen werden **nicht** automatisch ausgeführt. Nach Schemaänderungen manuell:

```bash
ssh transiv@37.27.37.136
cd /home/transiv/prognostic-fullstack
docker compose exec backend alembic upgrade head
```

---

## Neue Version releasen

```bash
# 1. VERSION-Datei anpassen
echo "1.0.2" > VERSION

# 2. CHANGELOG.md ergänzen

# 3. Committen und pushen
git add VERSION CHANGELOG.md
git commit -m "chore: release v1.0.2"
git push
# → GitHub Actions erstellt automatisch Git-Tag + GitHub Release
```

---

## Logs

```bash
# Container-Logs
ssh transiv@37.27.37.136 "docker logs forecast-frontend --tail 50"
ssh transiv@37.27.37.136 "docker logs forecast-backend --tail 50"

# App-Logs (Backend)
ssh transiv@37.27.37.136 "docker compose exec backend tail -f logs/app.log"
```

---

*Transivroom Division 2026*
