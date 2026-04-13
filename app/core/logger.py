"""
Zentrale Logging-Konfiguration für die Prognostic-API.

Schreibt strukturierte Logs in:
  - stdout (JSON, für Docker-Logs)
  - /app/logs/app.log (rotierend, 10 MB pro Datei, 5 Backups)
  - /app/logs/errors.log (nur ERROR+, rotierend)
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


LOG_DIR = os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class _JsonFormatter(logging.Formatter):
    """Gibt jeden Log-Eintrag als kompaktes JSON aus."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            payload.update(record.extra)  # type: ignore[arg-type]
        return json.dumps(payload, ensure_ascii=False)


def _setup() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    fmt = _JsonFormatter()

    # --- stdout ---
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # --- app.log (alle Level) ---
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # --- errors.log (nur ERROR+) ---
    eh = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "errors.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt)
    root.addHandler(eh)

    # Uvicorn-Logger auf selbes Level setzen
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


_setup()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
