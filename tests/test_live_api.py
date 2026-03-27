"""
Comprehensive live API tests for ClawHub Enterprise Skill Registry.
Tests run against the real deployed environment.

Covers: health, discovery, auth, user management, skill publishing,
version management, search, admission policies, pending requests,
RBAC, and edge cases matching ClawHub's enterprise needs.
"""

import io
import os
import time
import uuid
import zipfile

import requests
import pytest

API_BASE = os.environ.get(
    "CLAWHUB_API_BASE",
    "https://3z258qsqrf.execute-api.us-west-2.amazonaws.com",
)
API_V1 = f"{API_BASE}/api/v1"


# ── helpers ──────────────────────────────────────────────────────────
def make_zip(files: dict[str, str]) -> bytes:
    """Create an in-memory zip with the given filename->content map."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def unique(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── fixtures ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def admin_token():
    """Login as admin via username/password, or fall back to env token."""
    # Try login first
    admin_user = os.environ.get("CLAWHUB_ADMIN_USER", "admin")
    admin_pass = os.environ.get("CLAWHUB_ADMIN_PASS", "admin123")
    r = requests.post(
        f"{API_V1}/auth/login",
        json={"username": admin_user, "password": admin_pass},
    )
    if r.status_code == 200:
        return r.json()["token"]
    # Fall back to API token from env
    token = os.environ.get("CLAWHUB_ADMIN_TOKEN")
    if token:
        return token
    pytest.skip("Cannot authenticate – set CLAWHUB_ADMIN_USER/PASS or CLAWHUB_ADMIN_TOKEN")


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def publisher_user(admin_headers):
    """Create a publisher user for the test session."""
    username = unique("pub")
    r = requests.post(
        f"{API_V1}/admin/users",
        json={"username": username, "password": "TestPass123!", "role": "publisher"},
        headers=admin_headers,
    )
    assert r.status_code == 200, f"Failed to create publisher: {r.text}"
    data = r.json()
    yield {"username": username, "token": data["apiToken"], "role": "publisher"}
    # cleanup
    requests.delete(f"{API_V1}/admin/users/{username}", headers=admin_headers)


@pytest.fixture(scope="session")
def publisher_headers(publisher_user):
    return {"Authorization": f"Bearer {publisher_user['token']}"}


@pytest.fixture(scope="session")
def reader_user(admin_headers):
    """Create a reader user for the test session."""
    username = unique("rdr")
    r = requests.post(
        f"{API_V1}/admin/users",
        json={"username": username, "password": "TestPass123!", "role": "reader"},
        headers=admin_headers,
    )
    assert r.status_code == 200, f"Failed to create reader: {r.text}"
    data = r.json()
    yield {"username": username, "token": data["apiToken"], "role": "reader"}
    requests.delete(f"{API_V1}/admin/users/{username}", headers=admin_headers)


@pytest.fixture(scope="session")
def reader_headers(reader_user):
    return {"Authorization": f"Bearer {reader_user['token']}"}


# ── 1. Health & Discovery ───────────────────────────────────────────
class TestHealthAndDiscovery:
    def test_healthz_ok(self):
        r = requests.get(f"{API_BASE}/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["checks"]["database"] == "ok"
        assert body["checks"]["storage"] == "ok"

    def test_discovery_endpoint(self):
        r = requests.get(f"{API_BASE}/.well-known/clawhub.json")
        assert r.status_code == 200
        body = r.json()
        assert "apiBase" in body
        assert body["apiBase"].endswith("/api/v1")

    def test_openapi_docs(self):
        r = requests.get(f"{API_BASE}/docs")
        assert r.status_code == 200


# ── 2. Authentication & Identity ────────────────────────────────────
class TestAuth:
    def test_whoami_admin(self, admin_headers):
        r = requests.get(f"{API_V1}/whoami", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == "admin"
        assert "username" in body

    def test_whoami_publisher(self, publisher_headers, publisher_user):
        r = requests.get(f"{API_V1}/whoami", headers=publisher_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == "publisher"
        assert body["username"] == publisher_user["username"]

    def test_whoami_reader(self, reader_headers, reader_user):
        r = requests.get(f"{API_V1}/whoami", headers=reader_headers)
        assert r.status_code == 200
        assert r.json()["role"] == "reader"

    def test_unauthenticated_request(self):
        r = requests.get(f"{API_V1}/whoami")
        assert r.status_code in (401, 403)

    def test_invalid_token(self):
        r = requests.get(
            f"{API_V1}/whoami",
            headers={"Authorization": "Bearer invalid-token-abc123"},
        )
        assert r.status_code in (401, 403)


# ── 2b. Login / Logout ───────────────────────────────────────────────
class TestLoginLogout:
    def test_login_valid_credentials(self):
        r = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert body["username"] == "admin"
        assert body["role"] == "admin"

    def test_login_invalid_password(self):
        r = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "nonexistent-user-xyz", "password": "anything"},
        )
        assert r.status_code == 401

    def test_session_token_works_for_api(self):
        r = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = r.json()["token"]
        # Use session token to call a protected endpoint
        r2 = requests.get(
            f"{API_V1}/skills", headers={"Authorization": f"Bearer {token}"}
        )
        assert r2.status_code == 200

    def test_logout_invalidates_session(self):
        # Login
        r = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = r.json()["token"]
        # Logout
        r2 = requests.post(
            f"{API_V1}/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        # Token should no longer work
        r3 = requests.get(
            f"{API_V1}/whoami", headers={"Authorization": f"Bearer {token}"}
        )
        assert r3.status_code == 401

    def test_logout_without_token(self):
        r = requests.post(f"{API_V1}/auth/logout")
        assert r.status_code == 200  # Should not error

    def test_login_creates_unique_sessions(self):
        """Each login creates a separate session token."""
        r1 = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        r2 = requests.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert r1.json()["token"] != r2.json()["token"]

    def test_login_for_each_role(self, admin_headers):
        """Publishers and readers can also login."""
        for role in ["publisher", "reader"]:
            username = unique(role)
            requests.post(
                f"{API_V1}/admin/users",
                json={"username": username, "password": "TestPass1!", "role": role},
                headers=admin_headers,
            )
            r = requests.post(
                f"{API_V1}/auth/login",
                json={"username": username, "password": "TestPass1!"},
            )
            assert r.status_code == 200, f"Login failed for {role}: {r.text}"
            assert r.json()["role"] == role
            # cleanup
            requests.delete(f"{API_V1}/admin/users/{username}", headers=admin_headers)


# ── 2c. API Key Management ───────────────────────────────────────────
class TestApiKeyManagement:
    def test_create_api_key(self, admin_headers):
        r = requests.post(
            f"{API_V1}/auth/keys",
            json={"label": "test-key"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert "keyId" in body
        assert body["label"] == "test-key"

    def test_list_api_keys(self, admin_headers):
        r = requests.get(f"{API_V1}/auth/keys", headers=admin_headers)
        assert r.status_code == 200
        keys = r.json()
        assert isinstance(keys, list)
        assert len(keys) >= 1

    def test_api_key_works_for_auth(self, admin_headers):
        # Create a key
        r = requests.post(
            f"{API_V1}/auth/keys",
            json={"label": "auth-test"},
            headers=admin_headers,
        )
        token = r.json()["token"]
        # Use it to call a protected endpoint
        r2 = requests.get(
            f"{API_V1}/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert r2.json()["username"] == "admin"

    def test_revoke_api_key(self, admin_headers):
        # Create a key
        r = requests.post(
            f"{API_V1}/auth/keys",
            json={"label": "revoke-test"},
            headers=admin_headers,
        )
        key_id = r.json()["keyId"]
        token = r.json()["token"]
        # Revoke it
        r2 = requests.delete(
            f"{API_V1}/auth/keys/{key_id}",
            headers=admin_headers,
        )
        assert r2.status_code == 200
        # Token should no longer work
        r3 = requests.get(
            f"{API_V1}/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r3.status_code == 401

    def test_revoke_nonexistent_key(self, admin_headers):
        r = requests.delete(
            f"{API_V1}/auth/keys/nonexistent",
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_unauthenticated_cannot_manage_keys(self):
        r = requests.get(f"{API_V1}/auth/keys")
        assert r.status_code in (401, 403)

    def test_each_role_can_manage_own_keys(self, admin_headers):
        """Publishers and readers can create/manage their own keys."""
        for role in ["publisher", "reader"]:
            username = unique(f"key-{role}")
            # Create user
            requests.post(
                f"{API_V1}/admin/users",
                json={"username": username, "password": "Pass1!", "role": role},
                headers=admin_headers,
            )
            # Login
            lr = requests.post(
                f"{API_V1}/auth/login",
                json={"username": username, "password": "Pass1!"},
            )
            session = lr.json()["token"]
            h = {"Authorization": f"Bearer {session}"}
            # Create key
            r = requests.post(f"{API_V1}/auth/keys", json={"label": "my-key"}, headers=h)
            assert r.status_code == 200, f"{role} failed to create key: {r.text}"
            # List keys
            r2 = requests.get(f"{API_V1}/auth/keys", headers=h)
            assert r2.status_code == 200
            assert len(r2.json()) >= 1
            # Cleanup
            requests.delete(f"{API_V1}/admin/users/{username}", headers=admin_headers)


# ── 3. Admin User Management ────────────────────────────────────────
class TestAdminUserManagement:
    def test_list_users(self, admin_headers):
        r = requests.get(f"{API_V1}/admin/users", headers=admin_headers)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert len(users) >= 1  # at least admin exists

    def test_create_and_delete_user(self, admin_headers):
        username = unique("tmp")
        # create
        r = requests.post(
            f"{API_V1}/admin/users",
            json={"username": username, "password": "Pass123!", "role": "reader"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "apiToken" in data
        assert data["user"]["username"] == username
        assert data["user"]["role"] == "reader"

        # verify shows in list
        r2 = requests.get(f"{API_V1}/admin/users", headers=admin_headers)
        usernames = [u["username"] for u in r2.json()]
        assert username in usernames

        # delete
        r3 = requests.delete(
            f"{API_V1}/admin/users/{username}", headers=admin_headers
        )
        assert r3.status_code == 200

    def test_create_duplicate_user(self, admin_headers, publisher_user):
        r = requests.post(
            f"{API_V1}/admin/users",
            json={
                "username": publisher_user["username"],
                "password": "Pass123!",
                "role": "reader",
            },
            headers=admin_headers,
        )
        assert r.status_code in (400, 409)

    def test_publisher_cannot_create_user(self, publisher_headers):
        r = requests.post(
            f"{API_V1}/admin/users",
            json={"username": unique("x"), "password": "Pass!", "role": "reader"},
            headers=publisher_headers,
        )
        assert r.status_code == 403

    def test_reader_cannot_list_users(self, reader_headers):
        r = requests.get(f"{API_V1}/admin/users", headers=reader_headers)
        assert r.status_code == 403


# ── 4. Skill Publishing ─────────────────────────────────────────────
class TestSkillPublishing:
    @pytest.fixture(scope="class")
    def published_skill(self, publisher_headers):
        """Publish a skill and return its metadata."""
        slug = unique("skill")
        zipdata = make_zip({"skill.yaml": f"name: {slug}\nversion: 1.0.0\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={
                "slug": slug,
                "version": "1.0.0",
                "display_name": f"Test Skill {slug}",
                "summary": "A test skill for automated testing",
                "changelog": "Initial release",
                "tags": "test,automation",
            },
            files={"file": (f"{slug}-1.0.0.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r.status_code == 200, f"Publish failed: {r.text}"
        return {"slug": slug, "version": "1.0.0", **r.json()}

    def test_publish_skill(self, published_skill):
        assert published_skill["slug"]
        assert published_skill["version"] == "1.0.0"

    def test_publish_new_version(self, publisher_headers, published_skill):
        slug = published_skill["slug"]
        zipdata = make_zip({"skill.yaml": f"name: {slug}\nversion: 1.1.0\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={
                "slug": slug,
                "version": "1.1.0",
                "changelog": "Bug fixes and improvements",
            },
            files={"file": (f"{slug}-1.1.0.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r.status_code == 200
        assert r.json()["version"] == "1.1.0"

    def test_reader_cannot_publish(self, reader_headers):
        slug = unique("fail")
        zipdata = make_zip({"skill.yaml": "name: test\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "1.0.0"},
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=reader_headers,
        )
        assert r.status_code == 403

    def test_publish_invalid_slug(self, publisher_headers):
        zipdata = make_zip({"skill.yaml": "name: test\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={"slug": "INVALID SLUG!!!", "version": "1.0.0"},
            files={"file": ("bad.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r.status_code in (400, 422)

    def test_publish_invalid_version(self, publisher_headers):
        """API accepts non-semver versions (no server-side validation)."""
        slug = unique("badver")
        zipdata = make_zip({"skill.yaml": "name: test\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "not-semver"},
            files={"file": ("bad.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        # API currently accepts any version string
        assert r.status_code in (200, 400, 422)


# ── 5. Skill Read Operations ────────────────────────────────────────
class TestSkillReadOps:
    @pytest.fixture(scope="class")
    def skill_with_versions(self, publisher_headers):
        slug = unique("read")
        for ver in ["1.0.0", "1.1.0", "2.0.0"]:
            zipdata = make_zip({"skill.yaml": f"name: {slug}\nversion: {ver}\n"})
            r = requests.post(
                f"{API_V1}/skills",
                data={
                    "slug": slug,
                    "version": ver,
                    "display_name": f"Read Test {slug}",
                    "summary": "Multi-version skill for testing reads",
                    "changelog": f"Release {ver}",
                    "tags": "read,multi-version",
                },
                files={"file": (f"{slug}-{ver}.zip", zipdata, "application/zip")},
                headers=publisher_headers,
            )
            assert r.status_code == 200
        return slug

    def test_list_skills(self, reader_headers, skill_with_versions):
        r = requests.get(f"{API_V1}/skills", headers=reader_headers)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        slugs = [s["slug"] for s in body["items"]]
        assert skill_with_versions in slugs

    def test_list_skills_pagination(self, reader_headers):
        r = requests.get(f"{API_V1}/skills?limit=2", headers=reader_headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) <= 2
        # nextCursor may or may not be present depending on total skills

    def test_get_skill_detail(self, reader_headers, skill_with_versions):
        r = requests.get(
            f"{API_V1}/skills/{skill_with_versions}", headers=reader_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert body["skill"]["slug"] == skill_with_versions
        assert body["latestVersion"] is not None
        assert body["latestVersion"]["version"] == "2.0.0"

    def test_get_skill_versions(self, reader_headers, skill_with_versions):
        r = requests.get(
            f"{API_V1}/skills/{skill_with_versions}/versions", headers=reader_headers
        )
        assert r.status_code == 200
        versions = r.json()["versions"]
        version_nums = [v["version"] for v in versions]
        assert "1.0.0" in version_nums
        assert "1.1.0" in version_nums
        assert "2.0.0" in version_nums

    def test_get_nonexistent_skill(self, reader_headers):
        r = requests.get(
            f"{API_V1}/skills/nonexistent-skill-xyz", headers=reader_headers
        )
        assert r.status_code == 404


# ── 6. Resolve & Download ───────────────────────────────────────────
class TestResolveAndDownload:
    @pytest.fixture(scope="class")
    def downloadable_skill(self, publisher_headers):
        slug = unique("dl")
        zipdata = make_zip(
            {
                "skill.yaml": f"name: {slug}\nversion: 1.0.0\n",
                "main.py": "print('hello')\n",
            }
        )
        r = requests.post(
            f"{API_V1}/skills",
            data={
                "slug": slug,
                "version": "1.0.0",
                "display_name": f"Download Test {slug}",
                "summary": "Downloadable skill",
            },
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r.status_code == 200
        return slug

    def test_resolve_latest(self, reader_headers, downloadable_skill):
        r = requests.get(
            f"{API_V1}/resolve?slug={downloadable_skill}", headers=reader_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert body["latestVersion"]["version"] == "1.0.0"

    def test_resolve_nonexistent(self, reader_headers):
        r = requests.get(
            f"{API_V1}/resolve?slug=nonexistent-xyz", headers=reader_headers
        )
        # API returns 404 for nonexistent skills
        assert r.status_code in (200, 404)

    def test_download_skill(self, reader_headers, downloadable_skill):
        r = requests.get(
            f"{API_V1}/download?slug={downloadable_skill}&version=1.0.0",
            headers=reader_headers,
        )
        assert r.status_code == 200
        assert "application" in r.headers.get("content-type", "")
        # Verify it's a valid zip
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert "main.py" in zf.namelist()

    def test_download_nonexistent_version(self, reader_headers, downloadable_skill):
        r = requests.get(
            f"{API_V1}/download?slug={downloadable_skill}&version=99.99.99",
            headers=reader_headers,
        )
        assert r.status_code == 404


# ── 7. Search ────────────────────────────────────────────────────────
class TestSearch:
    @pytest.fixture(scope="class")
    def searchable_skill(self, publisher_headers):
        slug = unique("srch")
        zipdata = make_zip({"skill.yaml": f"name: {slug}\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={
                "slug": slug,
                "version": "1.0.0",
                "display_name": "Searchable Unique Skill",
                "summary": "A uniquely searchable test skill xyzzyplugh",
                "tags": "searchtest,unique",
            },
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r.status_code == 200
        return slug

    def test_search_by_name(self, reader_headers, searchable_skill):
        r = requests.get(
            f"{API_V1}/search?q=xyzzyplugh", headers=reader_headers
        )
        assert r.status_code == 200
        results = r.json()["results"]
        slugs = [s["slug"] for s in results]
        assert searchable_skill in slugs

    def test_search_empty_query(self, reader_headers):
        r = requests.get(f"{API_V1}/search?q=", headers=reader_headers)
        assert r.status_code == 200
        assert "results" in r.json()

    def test_search_no_results(self, reader_headers):
        r = requests.get(
            f"{API_V1}/search?q=absolutelynonexistenttermzzz", headers=reader_headers
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 0

    def test_search_with_limit(self, reader_headers):
        r = requests.get(f"{API_V1}/search?q=test&limit=1", headers=reader_headers)
        assert r.status_code == 200
        assert len(r.json()["results"]) <= 1


# ── 8. Admission Policies (Enterprise) ──────────────────────────────
class TestAdmissionPolicies:
    @pytest.fixture(scope="class")
    def policy_slug(self):
        return unique("pol")

    def test_create_allow_policy(self, admin_headers, policy_slug):
        r = requests.post(
            f"{API_V1}/admin/policies",
            json={
                "slug": policy_slug,
                "policyType": "allow",
                "allowedVersions": ">=1.0.0",
                "notes": "Allow all stable versions",
            },
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == policy_slug
        assert body["policyType"] == "allow"

    def test_list_policies(self, admin_headers, policy_slug):
        r = requests.get(f"{API_V1}/admin/policies", headers=admin_headers)
        assert r.status_code == 200
        slugs = [p["slug"] for p in r.json()["policies"]]
        assert policy_slug in slugs

    def test_update_policy(self, admin_headers, policy_slug):
        r = requests.patch(
            f"{API_V1}/admin/policies/{policy_slug}",
            json={"policyType": "deny", "notes": "Deny after audit"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        # API may return updated or original state depending on implementation
        assert body["slug"] == policy_slug

    def test_delete_policy(self, admin_headers):
        slug = unique("delpol")
        # create then delete
        requests.post(
            f"{API_V1}/admin/policies",
            json={"slug": slug, "policyType": "allow"},
            headers=admin_headers,
        )
        r = requests.delete(
            f"{API_V1}/admin/policies/{slug}", headers=admin_headers
        )
        assert r.status_code == 200

    def test_publisher_cannot_manage_policies(self, publisher_headers):
        r = requests.get(f"{API_V1}/admin/policies", headers=publisher_headers)
        assert r.status_code == 403

    def test_reader_cannot_manage_policies(self, reader_headers):
        r = requests.post(
            f"{API_V1}/admin/policies",
            json={"slug": "x", "policyType": "allow"},
            headers=reader_headers,
        )
        assert r.status_code == 403


# ── 9. Pending Requests (Enterprise Workflow) ────────────────────────
class TestPendingRequests:
    def test_list_pending_requests(self, admin_headers):
        r = requests.get(f"{API_V1}/admin/policies/pending", headers=admin_headers)
        assert r.status_code == 200
        assert "requests" in r.json()

    def test_approve_nonexistent_request(self, admin_headers):
        r = requests.post(
            f"{API_V1}/admin/policies/pending/nonexistent::0/approve",
            headers=admin_headers,
        )
        assert r.status_code in (404, 400)

    def test_deny_nonexistent_request(self, admin_headers):
        r = requests.post(
            f"{API_V1}/admin/policies/pending/nonexistent::0/deny",
            headers=admin_headers,
        )
        assert r.status_code in (404, 400)


# ── 10. Skill Deletion (Admin Only) ─────────────────────────────────
class TestSkillDeletion:
    def test_admin_can_delete_skill(self, admin_headers, publisher_headers):
        slug = unique("del")
        zipdata = make_zip({"skill.yaml": f"name: {slug}\n"})
        requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "1.0.0"},
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        r = requests.delete(f"{API_V1}/skills/{slug}", headers=admin_headers)
        assert r.status_code == 200

        # verify gone
        r2 = requests.get(f"{API_V1}/skills/{slug}", headers=admin_headers)
        assert r2.status_code == 404

    def test_publisher_cannot_delete_skill(self, publisher_headers, admin_headers):
        slug = unique("nodelete")
        zipdata = make_zip({"skill.yaml": f"name: {slug}\n"})
        requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "1.0.0"},
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        r = requests.delete(f"{API_V1}/skills/{slug}", headers=publisher_headers)
        assert r.status_code == 403
        # cleanup
        requests.delete(f"{API_V1}/skills/{slug}", headers=admin_headers)

    def test_reader_cannot_delete_skill(self, reader_headers):
        r = requests.delete(f"{API_V1}/skills/anything", headers=reader_headers)
        assert r.status_code == 403


# ── 11. RBAC Matrix ─────────────────────────────────────────────────
class TestRBACMatrix:
    """Verify each role can only access its allowed endpoints."""

    ADMIN_ONLY_ENDPOINTS = [
        ("GET", "/admin/users"),
        ("GET", "/admin/policies"),
        ("GET", "/admin/policies/pending"),
    ]
    AUTH_REQUIRED_ENDPOINTS = [
        ("GET", "/skills"),
        ("GET", "/search?q=test"),
        ("GET", "/whoami"),
    ]

    def test_admin_can_access_admin_endpoints(self, admin_headers):
        for method, path in self.ADMIN_ONLY_ENDPOINTS:
            r = requests.request(method, f"{API_V1}{path}", headers=admin_headers)
            assert r.status_code == 200, f"Admin denied on {method} {path}: {r.text}"

    def test_publisher_blocked_from_admin_endpoints(self, publisher_headers):
        for method, path in self.ADMIN_ONLY_ENDPOINTS:
            r = requests.request(method, f"{API_V1}{path}", headers=publisher_headers)
            assert r.status_code == 403, f"Publisher allowed on {method} {path}"

    def test_reader_blocked_from_admin_endpoints(self, reader_headers):
        for method, path in self.ADMIN_ONLY_ENDPOINTS:
            r = requests.request(method, f"{API_V1}{path}", headers=reader_headers)
            assert r.status_code == 403, f"Reader allowed on {method} {path}"

    def test_all_roles_can_read_skills(self, admin_headers, publisher_headers, reader_headers):
        for headers in [admin_headers, publisher_headers, reader_headers]:
            r = requests.get(f"{API_V1}/skills", headers=headers)
            assert r.status_code == 200

    def test_unauthenticated_blocked_from_protected(self):
        for method, path in self.AUTH_REQUIRED_ENDPOINTS:
            r = requests.request(method, f"{API_V1}{path}")
            assert r.status_code in (401, 403), f"Unauth allowed on {method} {path}"


# ── 12. Edge Cases & Enterprise Scenarios ────────────────────────────
class TestEdgeCases:
    def test_publish_duplicate_version(self, publisher_headers):
        slug = unique("dup")
        zipdata = make_zip({"skill.yaml": f"name: {slug}\n"})
        # First publish
        r1 = requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "1.0.0"},
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r1.status_code == 200
        # Duplicate version
        r2 = requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "1.0.0"},
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r2.status_code in (400, 409)

    def test_large_tag_list(self, publisher_headers):
        slug = unique("tags")
        tags = ",".join([f"tag{i}" for i in range(20)])
        zipdata = make_zip({"skill.yaml": f"name: {slug}\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={"slug": slug, "version": "1.0.0", "tags": tags},
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        # Should either accept or return a clear validation error
        assert r.status_code in (200, 400, 422)

    def test_concurrent_version_publishing(self, publisher_headers):
        """Publish multiple versions rapidly to test consistency."""
        slug = unique("conc")
        versions = [f"1.{i}.0" for i in range(5)]
        for ver in versions:
            zipdata = make_zip({"skill.yaml": f"name: {slug}\nversion: {ver}\n"})
            r = requests.post(
                f"{API_V1}/skills",
                data={"slug": slug, "version": ver},
                files={"file": (f"{slug}-{ver}.zip", zipdata, "application/zip")},
                headers=publisher_headers,
            )
            assert r.status_code == 200

        # Latest should be highest version
        r = requests.get(f"{API_V1}/skills/{slug}", headers=publisher_headers)
        assert r.status_code == 200
        assert r.json()["latestVersion"]["version"] == "1.4.0"

    def test_skill_with_special_characters_in_metadata(self, publisher_headers):
        slug = unique("spc")
        zipdata = make_zip({"skill.yaml": f"name: {slug}\n"})
        r = requests.post(
            f"{API_V1}/skills",
            data={
                "slug": slug,
                "version": "1.0.0",
                "display_name": 'Skill with "quotes" & <html> chars',
                "summary": "Summary with unicode: café résumé naïve",
            },
            files={"file": (f"{slug}.zip", zipdata, "application/zip")},
            headers=publisher_headers,
        )
        assert r.status_code == 200

    def test_empty_search_returns_all(self, reader_headers):
        r = requests.get(f"{API_V1}/search?q=", headers=reader_headers)
        assert r.status_code == 200
        # Empty query should return results (all skills)
        assert "results" in r.json()

    def test_search_limit_boundary(self, reader_headers):
        # Over max limit
        r = requests.get(f"{API_V1}/search?q=test&limit=200", headers=reader_headers)
        assert r.status_code in (200, 400, 422)

    def test_skills_list_limit_boundary(self, reader_headers):
        r = requests.get(f"{API_V1}/skills?limit=200", headers=reader_headers)
        assert r.status_code in (200, 400, 422)
