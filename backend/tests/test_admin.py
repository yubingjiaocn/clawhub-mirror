"""Tests for admin endpoints: users, policies, pending requests, proxy settings."""

from tests.conftest import auth_header


# --- User management ---

def test_create_user(client, admin_token):
    resp = client.post(
        "/api/v1/admin/users",
        json={"username": "newuser", "password": "pass123", "role": "reader"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == "newuser"
    assert body["user"]["role"] == "reader"
    assert "apiToken" in body


def test_create_duplicate_user_returns_409(client, admin_token):
    client.post(
        "/api/v1/admin/users",
        json={"username": "dupuser", "password": "pass123", "role": "reader"},
        headers=auth_header(admin_token),
    )
    resp = client.post(
        "/api/v1/admin/users",
        json={"username": "dupuser", "password": "pass456", "role": "reader"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 409


def test_create_user_invalid_role_returns_400(client, admin_token):
    resp = client.post(
        "/api/v1/admin/users",
        json={"username": "badrole", "password": "pass123", "role": "superadmin"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400


def test_list_users(client, admin_token):
    resp = client.get("/api/v1/admin/users", headers=auth_header(admin_token))
    assert resp.status_code == 200
    users = resp.json()
    assert any(u["username"] == "testadmin" for u in users)


def test_update_user_role(client, admin_token):
    client.post(
        "/api/v1/admin/users",
        json={"username": "promoteme", "password": "pass123", "role": "reader"},
        headers=auth_header(admin_token),
    )
    # Promote to publisher
    resp = client.patch(
        "/api/v1/admin/users/promoteme",
        json={"role": "publisher"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "publisher"

    # Promote to admin
    resp = client.patch(
        "/api/v1/admin/users/promoteme",
        json={"role": "admin"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    # Demote back to reader
    resp = client.patch(
        "/api/v1/admin/users/promoteme",
        json={"role": "reader"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "reader"


def test_update_user_role_invalid_returns_400(client, admin_token):
    client.post(
        "/api/v1/admin/users",
        json={"username": "badroleupdate", "password": "pass123", "role": "reader"},
        headers=auth_header(admin_token),
    )
    resp = client.patch(
        "/api/v1/admin/users/badroleupdate",
        json={"role": "superadmin"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400


def test_update_user_role_nonexistent_returns_404(client, admin_token):
    resp = client.patch(
        "/api/v1/admin/users/ghost-user",
        json={"role": "admin"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


def test_update_user_role_requires_admin(client, publisher_token):
    resp = client.patch(
        "/api/v1/admin/users/anyone",
        json={"role": "admin"},
        headers=auth_header(publisher_token),
    )
    assert resp.status_code == 403


def test_deactivate_user(client, admin_token):
    client.post(
        "/api/v1/admin/users",
        json={"username": "deactivateme", "password": "pass", "role": "reader"},
        headers=auth_header(admin_token),
    )
    resp = client.delete(
        "/api/v1/admin/users/deactivateme", headers=auth_header(admin_token)
    )
    assert resp.status_code == 200
    assert "deactivated" in resp.json()["detail"].lower()


def test_deactivate_nonexistent_user_returns_404(client, admin_token):
    resp = client.delete(
        "/api/v1/admin/users/ghost-user", headers=auth_header(admin_token)
    )
    assert resp.status_code == 404


# --- Admission policies ---

def test_policy_crud(client, admin_token):
    # Create
    resp = client.post(
        "/api/v1/admin/policies",
        json={"slug": "test-skill", "policy_type": "allow", "notes": "test policy"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    policy = resp.json()
    assert policy["slug"] == "test-skill"
    assert policy["policyType"] == "allow"
    assert policy["notes"] == "test policy"

    # List
    resp = client.get("/api/v1/admin/policies", headers=auth_header(admin_token))
    assert resp.status_code == 200
    policies = resp.json()["policies"]
    assert len(policies) >= 1
    assert any(p["slug"] == "test-skill" for p in policies)

    # Update type and notes
    resp = client.patch(
        "/api/v1/admin/policies/test-skill",
        json={"policy_type": "deny", "notes": "blocked after review"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["policyType"] == "deny"
    assert updated["notes"] == "blocked after review"
    assert updated["approvedBy"] == "testadmin"

    # Update only notes (type should remain deny)
    resp = client.patch(
        "/api/v1/admin/policies/test-skill",
        json={"notes": "updated notes only"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["policyType"] == "deny"
    assert resp.json()["notes"] == "updated notes only"

    # Delete
    resp = client.delete(
        "/api/v1/admin/policies/test-skill", headers=auth_header(admin_token)
    )
    assert resp.status_code == 200


def test_create_duplicate_policy_returns_409(client, admin_token):
    client.post(
        "/api/v1/admin/policies",
        json={"slug": "dup-policy", "policy_type": "allow"},
        headers=auth_header(admin_token),
    )
    resp = client.post(
        "/api/v1/admin/policies",
        json={"slug": "dup-policy", "policy_type": "deny"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 409


def test_update_nonexistent_policy_returns_404(client, admin_token):
    resp = client.patch(
        "/api/v1/admin/policies/no-such-policy",
        json={"policy_type": "deny"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


def test_delete_nonexistent_policy_returns_404(client, admin_token):
    resp = client.delete(
        "/api/v1/admin/policies/no-such-policy", headers=auth_header(admin_token)
    )
    assert resp.status_code == 404


def test_policy_invalid_type_returns_400(client, admin_token):
    resp = client.post(
        "/api/v1/admin/policies",
        json={"slug": "bad-type", "policy_type": "maybe"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400


def test_policy_update_invalid_type_returns_400(client, admin_token):
    client.post(
        "/api/v1/admin/policies",
        json={"slug": "valid-policy", "policy_type": "allow"},
        headers=auth_header(admin_token),
    )
    resp = client.patch(
        "/api/v1/admin/policies/valid-policy",
        json={"policy_type": "maybe"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400


# --- Proxy settings ---

def test_proxy_settings_default_disabled(client, admin_token):
    resp = client.get("/api/v1/admin/settings/proxy", headers=auth_header(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert "upstreamUrl" in body


def test_proxy_settings_toggle(client, admin_token):
    # Enable
    resp = client.put(
        "/api/v1/admin/settings/proxy",
        json={"enabled": True},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    # Verify
    resp = client.get("/api/v1/admin/settings/proxy", headers=auth_header(admin_token))
    assert resp.json()["enabled"] is True

    # Disable
    resp = client.put(
        "/api/v1/admin/settings/proxy",
        json={"enabled": False},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_proxy_settings_requires_admin(client, publisher_token):
    resp = client.get("/api/v1/admin/settings/proxy", headers=auth_header(publisher_token))
    assert resp.status_code == 403


# --- Pending requests ---

def test_pending_approve_deny_flow(client, admin_token):
    from app import dynamodb

    dynamodb.put_pending_request(slug="skill-a", requested_by="someone", reason="need it")
    dynamodb.put_pending_request(slug="skill-b", requested_by="other", reason="want it")

    # List pending
    resp = client.get("/api/v1/admin/policies/pending", headers=auth_header(admin_token))
    assert resp.status_code == 200
    pending = resp.json()["requests"]
    assert len(pending) == 2

    req_a_id = next(r["id"] for r in pending if r["slug"] == "skill-a")
    req_b_id = next(r["id"] for r in pending if r["slug"] == "skill-b")

    # Approve first
    resp = client.post(
        f"/api/v1/admin/policies/pending/{req_a_id}/approve",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == "skill-a"
    assert resp.json()["policyType"] == "allow"

    # Deny second
    resp = client.post(
        f"/api/v1/admin/policies/pending/{req_b_id}/deny",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert "denied" in resp.json()["detail"].lower()


def test_approve_nonexistent_pending_returns_404(client, admin_token):
    resp = client.post(
        "/api/v1/admin/policies/pending/fake::123/approve",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


def test_deny_nonexistent_pending_returns_404(client, admin_token):
    resp = client.post(
        "/api/v1/admin/policies/pending/fake::123/deny",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404
