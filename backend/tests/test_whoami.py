"""Tests for the whoami endpoint."""

from tests.conftest import auth_header


def test_whoami_returns_user_info(client, admin_token):
    resp = client.get("/api/v1/whoami", headers=auth_header(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "testadmin"
    assert body["role"] == "admin"
    assert body["handle"] == "testadmin"
