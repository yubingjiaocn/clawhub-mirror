"""Tests for skill CRUD, search, resolve, and download endpoints."""

from tests.conftest import auth_header, make_zip


def _publish(client, token, slug="my-skill", version="1.0.0", **kwargs):
    """Helper to publish a skill."""
    zf = make_zip()
    data = {
        "slug": slug,
        "version": version,
        "display_name": kwargs.get("display_name", "My Skill"),
        "summary": kwargs.get("summary", "A test skill"),
        "changelog": kwargs.get("changelog", "Initial release"),
        "tags": kwargs.get("tags", "test,demo"),
    }
    return client.post(
        "/api/v1/skills",
        data=data,
        files={"file": ("skill.zip", zf, "application/zip")},
        headers=auth_header(token),
    )


def test_publish_creates_skill(client, publisher_token):
    resp = _publish(client, publisher_token)
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "my-skill"
    assert body["version"] == "1.0.0"


def test_list_skills(client, publisher_token):
    _publish(client, publisher_token)
    resp = client.get("/api/v1/skills", headers=auth_header(publisher_token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) >= 1
    assert body["items"][0]["slug"] == "my-skill"


def test_get_skill_detail(client, publisher_token):
    _publish(client, publisher_token)
    resp = client.get("/api/v1/skills/my-skill", headers=auth_header(publisher_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["skill"]["slug"] == "my-skill"
    assert body["owner"]["handle"] == "testpublisher"


def test_get_skill_versions(client, publisher_token):
    _publish(client, publisher_token, version="1.0.0")
    _publish(client, publisher_token, version="1.1.0")
    resp = client.get(
        "/api/v1/skills/my-skill/versions", headers=auth_header(publisher_token)
    )
    assert resp.status_code == 200
    versions = resp.json()["versions"]
    assert len(versions) == 2
    version_strs = [v["version"] for v in versions]
    assert "1.0.0" in version_strs
    assert "1.1.0" in version_strs


def test_resolve_latest_version(client, publisher_token):
    _publish(client, publisher_token, version="1.0.0")
    _publish(client, publisher_token, version="2.0.0")
    resp = client.get(
        "/api/v1/resolve",
        params={"slug": "my-skill"},
        headers=auth_header(publisher_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["latestVersion"]["version"] == "2.0.0"


def test_download_returns_zip(client, publisher_token):
    _publish(client, publisher_token)
    resp = client.get(
        "/api/v1/download",
        params={"slug": "my-skill", "version": "1.0.0"},
        headers=auth_header(publisher_token),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    # ZIP magic bytes
    assert resp.content[:2] == b"PK"


def test_search_finds_skill(client, publisher_token):
    _publish(client, publisher_token, summary="A unique searchable description")
    resp = client.get(
        "/api/v1/search",
        params={"q": "unique searchable"},
        headers=auth_header(publisher_token),
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) >= 1
    assert results[0]["slug"] == "my-skill"


def test_delete_skill_admin_only(client, admin_token, publisher_token):
    _publish(client, publisher_token)
    # Publisher cannot delete
    resp = client.delete(
        "/api/v1/skills/my-skill", headers=auth_header(publisher_token)
    )
    assert resp.status_code == 403
    # Admin can delete
    resp = client.delete("/api/v1/skills/my-skill", headers=auth_header(admin_token))
    assert resp.status_code == 200
    # Skill is soft-deleted and no longer appears
    resp = client.get("/api/v1/skills/my-skill", headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_publish_duplicate_version_returns_409(client, publisher_token):
    _publish(client, publisher_token, version="1.0.0")
    resp = _publish(client, publisher_token, version="1.0.0")
    assert resp.status_code == 409


def test_invalid_slug_returns_400(client, publisher_token):
    resp = _publish(client, publisher_token, slug="INVALID SLUG!")
    assert resp.status_code == 400
