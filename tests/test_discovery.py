"""Tests for the discovery endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_well_known_endpoint(client: AsyncClient):
    """Test that /.well-known/clawhub.json returns correct API base."""
    resp = await client.get("/.well-known/clawhub.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "apiBase" in data
    assert data["apiBase"].endswith("/api/v1")


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    """Test health check endpoint."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
