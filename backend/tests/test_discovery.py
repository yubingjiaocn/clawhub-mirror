"""Tests for discovery and health endpoints."""

from tests.conftest import auth_header


def test_well_known_returns_api_base(client):
    resp = client.get("/.well-known/clawhub.json")
    assert resp.status_code == 200
    body = resp.json()
    assert "apiBase" in body
    assert body["apiBase"].endswith("/api/v1")


def test_healthz_returns_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["storage"] == "ok"
