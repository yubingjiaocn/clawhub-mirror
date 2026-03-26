"""Tests for admin endpoints: users, policies, pending requests."""

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


def test_list_users(client, admin_token):
    resp = client.get("/api/v1/admin/users", headers=auth_header(admin_token))
    assert resp.status_code == 200
    users = resp.json()
    # At least the admin user we seeded
    assert any(u["username"] == "testadmin" for u in users)


def test_deactivate_user(client, admin_token):
    # Create a user first
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

    # List
    resp = client.get("/api/v1/admin/policies", headers=auth_header(admin_token))
    assert resp.status_code == 200
    policies = resp.json()["policies"]
    assert len(policies) >= 1

    # Update
    resp = client.patch(
        "/api/v1/admin/policies/test-skill",
        json={"policy_type": "deny", "notes": "updated"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["policyType"] == "deny"

    # Delete
    resp = client.delete(
        "/api/v1/admin/policies/test-skill", headers=auth_header(admin_token)
    )
    assert resp.status_code == 200


# --- Pending requests ---

def test_pending_approve_deny_flow(client, admin_token):
    from app import dynamodb

    # Seed two pending requests
    req1 = dynamodb.put_pending_request(slug="skill-a", requested_by="someone", reason="need it")
    req2 = dynamodb.put_pending_request(slug="skill-b", requested_by="other", reason="want it")

    # List pending
    resp = client.get("/api/v1/admin/policies/pending", headers=auth_header(admin_token))
    assert resp.status_code == 200
    pending = resp.json()["requests"]
    assert len(pending) == 2

    # Build request IDs from the pending list
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
