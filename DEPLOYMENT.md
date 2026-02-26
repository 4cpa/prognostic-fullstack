# Deployment Guide – Prognostic Fullstack

## 🚀 Production Deployment Workflow

This project follows an immutable server deployment strategy.

### 🔒 Core Principle

The VPS (transivroom) is never modified manually.
All changes must:

1. Be developed and tested locally (dispatch)
2. Be committed and pushed to GitHub
3. Be merged into `main`
4. Be deployed automatically via GitHub Actions

Direct edits on the production server are forbidden except in absolute emergency cases.

---

## 🖥 Environments

### Local Development
Machine: dispatch  
Path: `~/prognostic-fullstack`

Used for:
- Feature development
- Testing
- Docker validation

### Production
Server: transivroom  
Path: `/srv/4cpa/prognostic-fullstack`

Deployment method:
- `git pull` (temporary, legacy)
- Preferred: GitHub Actions SSH deploy

---

## 🔄 Standard Deployment Process

1. Create feature branch:
   ```bash
   git checkout -b feature/xyz
