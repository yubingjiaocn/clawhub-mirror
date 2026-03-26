"""Tests for authentication and authorization."""

from tests.conftest import auth_header


def test_request_without_token_returns_401(client):
    resp = client.get("/api/v1/skills")
    assert resp.status_code == 401


def test_request_with_invalid_token_returns_401(client):
    resp = client.get("/api/v1/skills", headers=auth_header("bogus-token-abc"))
    assert resp.status_code == 401


def test_admin_token_works_for_admin_endpoints(client, admin_token):
    resp = client.get("/api/v1/admin/users", headers=auth_header(admin_token))
    assert resp.status_code == 200


def test_publisher_rejected_on_admin_endpoints(client, publisher_token):
    resp = client.get("/api/v1/admin/users", headers=auth_header(publisher_token))
    assert resp.status_code == 403
