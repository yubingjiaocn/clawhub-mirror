"""Tests for proxy/admission logic."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unadmitted_skill_returns_403(client: AsyncClient, reader_token: str):
    """Test that requesting a non-local, non-admitted skill returns 403."""
    resp = await client.get(
        "/api/v1/resolve",
        params={"slug": "external-skill"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    # Should be 403 since proxy.check_admission returns False by default
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unadmitted_download_returns_403(client: AsyncClient, reader_token: str):
    """Test that downloading a non-admitted external skill returns 403."""
    resp = await client.get(
        "/api/v1/download",
        params={"slug": "external-skill", "version": "1.0.0"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 403
