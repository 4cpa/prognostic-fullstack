"""
Integrationstests: Questions-API (CRUD + Auflösung).
"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration

_QUESTION_PAYLOAD = {
    "title": "Test: Wird X passieren?",
    "description": "Eine Testfrage für automatisierte Tests.",
    "category": "test",
    "region": "EU",
    "country": "DE",
    "resolve_at": "2026-12-31T23:59:59",
    "resolution_criteria": "Tritt X vor dem 31.12.2026 ein?",
    "resolution_source_policy": "public_news",
}


@pytest.fixture
def created_question(client):
    """Erstellt eine Frage und gibt die Response-JSON zurück."""
    r = client.post("/questions", json=_QUESTION_PAYLOAD)
    assert r.status_code == 200, r.text
    return r.json()


def test_create_question_returns_id(client):
    r = client.post("/questions", json=_QUESTION_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["title"] == _QUESTION_PAYLOAD["title"]
    assert data["status"] == "open"


def test_get_question_by_id(client, created_question):
    qid = created_question["id"]
    r = client.get(f"/questions/{qid}")
    assert r.status_code == 200
    assert r.json()["id"] == qid


def test_get_nonexistent_question_returns_404(client):
    r = client.get("/questions/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_add_evidence_to_question(client, created_question):
    qid = created_question["id"]
    payload = {
        "indicator_type": "expert_opinion",
        "direction": "pro",
        "weight": 0.7,
        "note": "Expertenmeinung aus Test",
    }
    r = client.post(f"/questions/{qid}/evidence", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["direction"] == "pro"
    assert data["question_id"] == qid


def test_list_evidence_for_question(client, created_question):
    qid = created_question["id"]
    # Erst Evidenz hinzufügen
    client.post(f"/questions/{qid}/evidence", json={
        "indicator_type": "market_signal",
        "direction": "contra",
        "weight": 0.5,
    })
    r = client.get(f"/questions/{qid}/evidence")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_resolve_question_yes(client, created_question):
    qid = created_question["id"]
    r = client.post(f"/questions/{qid}/resolve", params={"outcome": "yes"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "resolved_yes"
    assert data["resolved_at"] is not None


def test_resolve_question_invalid_outcome(client, created_question):
    qid = created_question["id"]
    r = client.post(f"/questions/{qid}/resolve", params={"outcome": "maybe"})
    assert r.status_code == 400
