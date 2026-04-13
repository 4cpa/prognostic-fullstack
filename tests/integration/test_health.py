"""
Integrationstests: Health-Endpunkt & grundlegende API-Erreichbarkeit.
"""
import pytest


pytestmark = pytest.mark.integration


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint_exists(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "HELP" in response.text
