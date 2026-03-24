"""Tests for admin endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, admin_token: str):
    """Test admin can create a new user."""
    resp = await client.post(
        "/api/v1/admin/users",
        json={"username": "newuser", "password": "secret123", "role": "reader"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "newuser"
    assert "apiToken" in data


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, admin_token: str):
    """Test admin can list users."""
    resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_admission_policy(client: AsyncClient, admin_token: str):
    """Test creating an admission policy."""
    resp = await client.post(
        "/api/v1/admin/policies",
        json={
            "slug": "allowed-skill",
            "policy_type": "allow",
            "notes": "Approved for internal use",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "allowed-skill"
    assert data["policyType"] == "allow"


@pytest.mark.asyncio
async def test_list_policies(client: AsyncClient, admin_token: str):
    """Test listing admission policies."""
    resp = await client.get(
        "/api/v1/admin/policies",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "policies" in data


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_routes(client: AsyncClient, reader_token: str):
    """Test that non-admin users cannot access admin endpoints."""
    resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_policy(client: AsyncClient, admin_token: str):
    """Test deleting an admission policy."""
    # Create first
    await client.post(
        "/api/v1/admin/policies",
        json={"slug": "to-delete", "policy_type": "allow"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.delete(
        "/api/v1/admin/policies/to-delete",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
