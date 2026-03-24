"""Tests for skill CRUD and search endpoints."""

import io
import zipfile

import pytest
from httpx import AsyncClient


def make_skill_zip(skill_md: str = "# Test Skill\nA test skill.") -> bytes:
    """Create a minimal skill zip file in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("SKILL.md", skill_md)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_publish_and_get_skill(client: AsyncClient, publisher_token: str):
    """Test publishing a skill and retrieving it."""
    zip_data = make_skill_zip()
    resp = await client.post(
        "/api/v1/skills",
        data={
            "slug": "test-skill",
            "version": "1.0.0",
            "display_name": "Test Skill",
            "summary": "A test skill for unit tests",
            "changelog": "Initial release",
            "tags": "test,example",
        },
        files={"file": ("test-skill.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "test-skill"
    assert data["version"] == "1.0.0"

    # Get skill detail
    resp = await client.get(
        "/api/v1/skills/test-skill",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill"]["slug"] == "test-skill"
    assert data["latestVersion"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_list_skills(client: AsyncClient, publisher_token: str):
    """Test listing skills with pagination."""
    # Publish a skill first
    zip_data = make_skill_zip()
    await client.post(
        "/api/v1/skills",
        data={"slug": "list-test", "version": "0.1.0"},
        files={"file": ("s.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.get(
        "/api/v1/skills",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_resolve_skill(client: AsyncClient, publisher_token: str):
    """Test resolving a skill version."""
    zip_data = make_skill_zip()
    await client.post(
        "/api/v1/skills",
        data={"slug": "resolve-test", "version": "2.0.0"},
        files={"file": ("s.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.get(
        "/api/v1/resolve",
        params={"slug": "resolve-test"},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["latestVersion"]["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_download_skill(client: AsyncClient, publisher_token: str):
    """Test downloading a skill zip."""
    zip_data = make_skill_zip()
    await client.post(
        "/api/v1/skills",
        data={"slug": "dl-test", "version": "1.0.0"},
        files={"file": ("s.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.get(
        "/api/v1/download",
        params={"slug": "dl-test", "version": "1.0.0"},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_delete_skill_requires_admin(client: AsyncClient, publisher_token: str):
    """Test that only admins can delete skills."""
    zip_data = make_skill_zip()
    await client.post(
        "/api/v1/skills",
        data={"slug": "del-test", "version": "1.0.0"},
        files={"file": ("s.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.delete(
        "/api/v1/skills/del-test",
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_skill_as_admin(client: AsyncClient, admin_token: str, publisher_token: str):
    """Test admin can soft-delete a skill."""
    zip_data = make_skill_zip()
    await client.post(
        "/api/v1/skills",
        data={"slug": "admin-del", "version": "1.0.0"},
        files={"file": ("s.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )

    resp = await client.delete(
        "/api/v1/skills/admin-del",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Skill should not appear anymore
    resp = await client.get(
        "/api/v1/skills/admin-del",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_slug_rejected(client: AsyncClient, publisher_token: str):
    """Test that invalid slugs are rejected."""
    zip_data = make_skill_zip()
    resp = await client.post(
        "/api/v1/skills",
        data={"slug": "INVALID_SLUG!", "version": "1.0.0"},
        files={"file": ("s.zip", zip_data, "application/zip")},
        headers={"Authorization": f"Bearer {publisher_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    """Test that unauthenticated requests are rejected."""
    resp = await client.get("/api/v1/skills")
    assert resp.status_code == 401
