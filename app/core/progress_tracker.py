"""In-memory stage tracking for long-running forecast generation.

Single-process, single-worker deployment (see Dockerfile: plain `uvicorn
app.main:app`, no --workers), so a module-level dict guarded by a lock is
sufficient — no DB table or external store needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Optional

_lock = Lock()
_stages: dict[str, dict[str, str]] = {}


def set_stage(question_id: Optional[str], stage: str) -> None:
    if not question_id:
        return
    with _lock:
        _stages[question_id] = {
            "stage": stage,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


def get_stage(question_id: str) -> Optional[dict[str, str]]:
    with _lock:
        entry = _stages.get(question_id)
        return dict(entry) if entry else None


def clear_stage(question_id: Optional[str]) -> None:
    if not question_id:
        return
    with _lock:
        _stages.pop(question_id, None)
