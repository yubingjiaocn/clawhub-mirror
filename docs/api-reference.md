# API Reference

Base URL: `https://<your-deployment>/api/v1`

All authenticated endpoints require `Authorization: Bearer <token>` header. Tokens can be either session tokens (from login) or API keys (from Settings page or `POST /auth/keys`).

---

## Authentication

### POST /auth/login

Login with username and password. Returns a session token.

**Auth:** None

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "token": "session-token-string",
  "username": "admin",
  "role": "admin"
}
```

**Errors:** `401` Invalid credentials or deactivated account.

---

### POST /auth/register

Create a new account. Returns a session token (auto-login).

**Auth:** None

**Request:**
```json
{
  "username": "string (3+ chars, alphanumeric/hyphens/underscores)",
  "password": "string (6+ chars)"
}
```

**Response (200):**
```json
{
  "token": "session-token-string",
  "username": "newuser",
  "role": "reader"
}
```

**Errors:** `400` Validation error. `409` Username already taken.

---

### POST /auth/logout

Invalidate the current session token.

**Auth:** Optional (invalidates provided token if present)

**Response (200):**
```json
{
  "detail": "Logged out."
}
```

---

## User Info

### GET /whoami

Return current user info. Compatible with both the ClawHub CLI format and extended fields.

**Auth:** Required (any role)

**Response (200):**
```json
{
  "user": {
    "handle": "admin",
    "displayName": "admin",
    "image": null
  },
  "username": "admin",
  "role": "admin",
  "handle": "admin"
}
```

---

## API Key Management

### GET /auth/keys

List active API keys for the current user.

**Auth:** Required (any role)

**Response (200):**
```json
[
  {
    "keyId": "abc12345",
    "label": "my-laptop",
    "tokenPrefix": "abc12345abcd",
    "createdAt": 1711500000000
  }
]
```

---

### POST /auth/keys

Generate a new API key.

**Auth:** Required (any role)

**Request:**
```json
{
  "label": "optional description"
}
```

**Response (200):**
```json
{
  "keyId": "abc12345",
  "label": "optional description",
  "token": "full-api-key-shown-only-once",
  "createdAt": 1711500000000
}
```

**Errors:** `400` Maximum of 10 keys per user.

---

### DELETE /auth/keys/{keyId}

Revoke an API key. The key immediately stops working.

**Auth:** Required (owner of the key)

**Response (200):**
```json
{
  "detail": "API key revoked."
}
```

**Errors:** `404` Key not found.

---

## Skills

### GET /skills

List all skills, sorted by most recently updated.

**Auth:** Required (any role)

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Results per page (1-100) |
| `cursor` | string | — | Pagination cursor from previous response |

**Response (200):**
```json
{
  "items": [
    {
      "slug": "git-essentials",
      "displayName": "Git Essentials",
      "summary": "Essential Git commands...",
      "tags": ["latest"],
      "stats": { "downloads": 0, "stars": 0 },
      "createdAt": 1711500000000,
      "updatedAt": 1711500000000,
      "latestVersion": {
        "version": "1.0.0",
        "createdAt": 1711500000000,
        "changelog": "Initial release"
      }
    }
  ],
  "nextCursor": "base64-encoded-cursor-or-null"
}
```

---

### GET /skills/{slug}

Get full detail for a single skill.

**Auth:** Required (any role)

**Response (200):**
```json
{
  "skill": {
    "slug": "git-essentials",
    "displayName": "Git Essentials",
    "summary": "Essential Git commands...",
    "tags": ["latest"],
    "stats": { "downloads": 0, "stars": 0 },
    "createdAt": 1711500000000,
    "updatedAt": 1711500000000,
    "latestVersion": { "version": "1.1.0", "createdAt": 1711500000000, "changelog": null }
  },
  "latestVersion": { "version": "1.1.0", "createdAt": 1711500000000, "changelog": null },
  "owner": {
    "handle": "admin",
    "displayName": "admin"
  }
}
```

**Errors:** `404` Skill not found.

---

### GET /skills/{slug}/versions

List all versions of a skill, newest first.

**Auth:** Required (any role)

**Response (200):**
```json
{
  "versions": [
    { "version": "1.1.0", "createdAt": 1711500000000, "changelog": "Bug fixes" },
    { "version": "1.0.0", "createdAt": 1711400000000, "changelog": "Initial release" }
  ]
}
```

---

### GET /search

Search skills by name, slug, or summary.

**Auth:** Required (any role)

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | `""` | Search query (empty returns all) |
| `limit` | int | 20 | Max results (1-100) |

**Response (200):**
```json
{
  "results": [
    {
      "slug": "git-essentials",
      "displayName": "Git Essentials",
      "summary": "Essential Git commands...",
      "version": "1.1.0",
      "score": 1.0,
      "updatedAt": 1711500000000
    }
  ]
}
```

---

### GET /resolve

Resolve the latest version of a skill. Used by the `clawhub` CLI during `install`.

**Auth:** Required (any role)

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | Yes | Skill slug |
| `hash` | string | No | Content hash to match a specific version |

**Response (200):**
```json
{
  "match": { "version": "1.0.0" },
  "latestVersion": { "version": "1.1.0", "createdAt": 1711500000000, "changelog": null }
}
```

`match` is `null` if no hash match. `latestVersion` is always the newest version.

**Errors:** `404` Skill not found.

---

### GET /download

Download a skill version as a zip archive.

**Auth:** Required (any role)

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | Yes | Skill slug |
| `version` | string | Yes | Version string |

**Response (200):** Binary `application/zip` with `Content-Disposition: attachment`.

**Errors:** `404` Version or archive not found.

---

### POST /skills

Publish a new skill or a new version of an existing skill.

**Auth:** Required (admin or publisher role)

Accepts **two multipart formats:**

#### Format 1: clawhub CLI format

| Field | Type | Description |
|-------|------|-------------|
| `payload` | JSON string | `{"slug", "version", "displayName", "description", "changelog", "tags", "acceptLicenseTerms"}` |
| `files` | File(s) | Skill files (assembled into a zip) |

#### Format 2: Form field format

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | Skill slug (lowercase, alphanumeric, hyphens) |
| `version` | string | Semantic version |
| `display_name` | string? | Human-readable name |
| `summary` | string? | Short description |
| `changelog` | string? | Version changelog |
| `tags` | string? | Comma-separated tags |
| `file` | File | Zip archive |

**Response (200):**
```json
{
  "ok": true,
  "skillId": "git-essentials",
  "versionId": "git-essentials@1.0.0",
  "slug": "git-essentials",
  "version": "1.0.0",
  "message": "Published successfully"
}
```

**Errors:** `400` Invalid slug or empty file. `409` Version already exists.

---

### DELETE /skills/{slug}

Soft-delete a skill (hides from listings and search).

**Auth:** Required (admin role only)

**Response (200):**
```json
{
  "message": "Skill deleted"
}
```

---

## Admin: User Management

### POST /admin/users

Create a new user.

**Auth:** Required (admin role)

**Request:**
```json
{
  "username": "string",
  "password": "string",
  "role": "reader | publisher | admin"
}
```

**Response (200):**
```json
{
  "user": {
    "username": "newuser",
    "role": "publisher",
    "isActive": true,
    "createdAt": 1711500000000
  },
  "apiToken": "generated-api-token"
}
```

**Errors:** `409` Username exists. `400` Invalid role.

---

### GET /admin/users

List all users.

**Auth:** Required (admin role)

**Response (200):**
```json
[
  {
    "username": "admin",
    "role": "admin",
    "isActive": true,
    "createdAt": 1711500000000
  }
]
```

---

### DELETE /admin/users/{username}

Deactivate a user. Their tokens stop working immediately.

**Auth:** Required (admin role)

**Response (200):**
```json
{
  "detail": "User admin has been deactivated."
}
```

---

## Admin: Proxy Settings

### GET /admin/settings/proxy

Get the current proxy configuration.

**Auth:** Required (admin role)

**Response (200):**

```json
{
  "enabled": false,
  "upstreamUrl": "https://clawhub.ai"
}
```

---

### PUT /admin/settings/proxy

Enable or disable the public ClawHub proxy.

**Auth:** Required (admin role)

**Request:**

```json
{
  "enabled": true,
  "upstream_url": "https://clawhub.ai"
}
```

`upstream_url` is optional (defaults to `https://clawhub.ai`).

**Response (200):**

```json
{
  "enabled": true,
  "upstreamUrl": "https://clawhub.ai"
}
```

When enabled, the following endpoints will proxy to upstream for skills not found locally:
- `GET /resolve` -- resolve version from upstream
- `GET /download` -- download archive from upstream (cached in S3)
- `GET /search` -- merge local + upstream results
- `GET /skills/{slug}` -- fetch skill detail from upstream (cached in DynamoDB)
- `GET /skills/{slug}/versions` -- fetch versions from upstream

Cached skills are marked with `isExternal: true` and remain accessible even after disabling the proxy.

---

## Admin: Admission Policies

### GET /admin/policies

List all admission policies.

**Auth:** Required (admin role)

**Response (200):**
```json
{
  "policies": [
    {
      "id": "my-skill",
      "slug": "my-skill",
      "allowedVersions": ">=1.0.0",
      "policyType": "allow",
      "approvedBy": "admin",
      "approvedAt": 1711500000000,
      "notes": "Approved for production",
      "createdAt": 1711500000000
    }
  ]
}
```

---

### POST /admin/policies

Create an admission policy.

**Auth:** Required (admin role)

**Request:**
```json
{
  "slug": "skill-slug",
  "policyType": "allow | deny",
  "allowedVersions": ">=1.0.0 (optional)",
  "notes": "optional notes"
}
```

**Errors:** `409` Policy already exists for this slug.

---

### PATCH /admin/policies/{slug}

Update an existing policy.

**Auth:** Required (admin role)

**Request (all fields optional):**
```json
{
  "policyType": "deny",
  "allowedVersions": ">=2.0.0",
  "notes": "Updated policy"
}
```

---

### DELETE /admin/policies/{slug}

Delete a policy.

**Auth:** Required (admin role)

---

### GET /admin/policies/pending

List pending approval requests.

**Auth:** Required (admin role)

**Response (200):**
```json
{
  "requests": [
    {
      "id": "my-skill::1711500000000",
      "slug": "my-skill",
      "requestedBy": "publisher1",
      "requestedAt": 1711500000000,
      "reason": "Need this for project X",
      "status": "pending"
    }
  ]
}
```

---

### POST /admin/policies/pending/{requestId}/approve

Approve a pending request (creates an allow policy).

**Auth:** Required (admin role)

---

### POST /admin/policies/pending/{requestId}/deny

Deny a pending request.

**Auth:** Required (admin role)

---

## Discovery

### GET /.well-known/clawhub.json

Registry discovery endpoint. Used by the `clawhub` CLI to find the API base URL.

**Auth:** None

**Response (200):**
```json
{
  "apiBase": "https://your-deployment.example.com"
}
```

The CLI appends `/api/v1` to `apiBase` for all subsequent requests.

---

### GET /healthz

Health check. Returns status of database and storage backends.

**Auth:** None

**Response (200):**
```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "storage": "ok"
  }
}
```

**Response (503):** `status: "degraded"` with error details in `checks`.

---

## Error Format

All errors return JSON:

```json
{
  "detail": "Human-readable error message"
}
```

Or for validation errors (422):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "slug"],
      "msg": "Field required"
    }
  ]
}
```

## Rate Limits

No rate limits are enforced by the application. API Gateway and CloudFront default limits apply.

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request / validation error |
| 401 | Missing or invalid token |
| 403 | Insufficient role permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate) |
| 422 | Validation error (FastAPI) |
| 503 | Service degraded |
