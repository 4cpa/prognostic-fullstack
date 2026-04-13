"""
Gemeinsame pytest-Fixtures für Unit- und Integrationstests.

Für Integrationstests wird eine SQLite-In-Memory-Datenbank verwendet,
damit keine laufende PostgreSQL-Instanz erforderlich ist.
"""
from __future__ import annotations

import logging
import os
import pytest

from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

# Umgebungsvariablen vor dem Import von App-Code setzen
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GEMINI_API_KEY", "")

log = logging.getLogger("tests")


# ---------------------------------------------------------------------------
# Datenbank-Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """SQLite-In-Memory-Engine für die gesamte Test-Session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Frische DB-Session pro Test; Rollback nach jedem Test."""
    with Session(engine) as s:
        yield s
        s.rollback()


# ---------------------------------------------------------------------------
# HTTP-Client-Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client(engine):
    """TestClient mit überschriebener DB-Session."""
    from fastapi.testclient import TestClient  # httpx muss installiert sein
    from app.main import app
    from app.core.db import get_session

    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
