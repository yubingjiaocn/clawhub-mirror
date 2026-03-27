"""Tests for authentication and authorization."""

from tests.conftest import auth_header


# --- Token auth ---

def test_request_without_token_returns_401(client):
    resp = client.get("/api/v1/skills")
    assert resp.status_code == 401


def test_request_with_invalid_token_returns_401(client):
    resp = client.get("/api/v1/skills", headers=auth_header("bogus-token-abc"))
    assert resp.status_code == 401


def test_empty_bearer_token_returns_401(client):
    resp = client.get("/api/v1/skills", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


def test_admin_token_works_for_admin_endpoints(client, admin_token):
    resp = client.get("/api/v1/admin/users", headers=auth_header(admin_token))
    assert resp.status_code == 200


def test_publisher_rejected_on_admin_endpoints(client, publisher_token):
    resp = client.get("/api/v1/admin/users", headers=auth_header(publisher_token))
    assert resp.status_code == 403


# --- Login / Register / Logout ---

def test_register_and_login(client):
    # Register
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "password": "securepass"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "newuser"
    assert body["role"] == "reader"
    assert "token" in body

    # Login with same credentials
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "newuser", "password": "securepass"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "newuser"
    token = resp.json()["token"]

    # Whoami with session token
    resp = client.get("/api/v1/whoami", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "newuser"

    # Logout
    resp = client.post("/api/v1/auth/logout", headers=auth_header(token))
    assert resp.status_code == 200

    # Token invalidated after logout
    resp = client.get("/api/v1/whoami", headers=auth_header(token))
    assert resp.status_code == 401


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "logintest", "password": "correct"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "logintest", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user_returns_401(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_register_duplicate_returns_409(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "dupuser", "password": "pass123"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "dupuser", "password": "pass456"},
    )
    assert resp.status_code == 409


def test_register_short_username_returns_400(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "password": "pass123"},
    )
    assert resp.status_code == 400


def test_register_short_password_returns_400(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "validname", "password": "short"},
    )
    assert resp.status_code == 400


# --- API Keys ---

def test_api_key_crud(client):
    # Register to get a session
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "keyuser", "password": "securepass"},
    )
    token = resp.json()["token"]

    # List keys (empty)
    resp = client.get("/api/v1/auth/keys", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == []

    # Create key
    resp = client.post(
        "/api/v1/auth/keys",
        json={"label": "test-key"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    key_data = resp.json()
    assert key_data["label"] == "test-key"
    assert "token" in key_data
    api_key = key_data["token"]
    key_id = key_data["keyId"]

    # List keys (one)
    resp = client.get("/api/v1/auth/keys", headers=auth_header(token))
    assert len(resp.json()) == 1

    # Use API key to authenticate
    resp = client.get("/api/v1/whoami", headers=auth_header(api_key))
    assert resp.status_code == 200
    assert resp.json()["username"] == "keyuser"

    # Revoke key
    resp = client.delete(f"/api/v1/auth/keys/{key_id}", headers=auth_header(token))
    assert resp.status_code == 200

    # Revoked key no longer works
    resp = client.get("/api/v1/whoami", headers=auth_header(api_key))
    assert resp.status_code == 401

    # List keys (empty again)
    resp = client.get("/api/v1/auth/keys", headers=auth_header(token))
    assert resp.json() == []


def test_deactivated_user_cannot_login(client, admin_token):
    # Create and deactivate a user
    client.post(
        "/api/v1/admin/users",
        json={"username": "willdeactivate", "password": "pass123", "role": "reader"},
        headers=auth_header(admin_token),
    )
    client.delete("/api/v1/admin/users/willdeactivate", headers=auth_header(admin_token))

    # Cannot login
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "willdeactivate", "password": "pass123"},
    )
    assert resp.status_code == 401
