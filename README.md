# ClawHub Mirror

**Enterprise skill registry proxy for ClawHub**

ClawHub Mirror is a self-hosted, ClawHub-compatible skill registry that operates as a transparent proxy and local cache in front of the public ClawHub registry. It gives organizations full control over which skills are available to their teams through an admission-policy workflow, while also supporting publishing and hosting private, internal skills.

---

## Architecture

ClawHub Mirror sits between the ClawHub CLI and the upstream public registry. It intercepts all skill operations, serves locally published skills directly, and forwards approved external skill requests to the upstream registry while caching the results.

```
                         +---------------------+
                         |   clawhub-mirror    |
                         |                     |
  ClawHub CLI  --------> |  FastAPI (v1 API)   |
  (resolve,              |                     |
   download,    <------- |  +---------------+  |-------> upstream
   search,               |  | SQLite / PG   |  |        clawhub.ai
   publish)              |  +---------------+  |  <------- (proxy &
                         |  +---------------+  |           cache)
                         |  | Local / S3    |  |
                         |  | File Storage  |  |
                         |  +---------------+  |
                         +---------------------+
```

**Key concepts:**

- **Local skills** -- published directly to the mirror by authorized users; served without contacting upstream.
- **External skills** -- requested by the CLI but not published locally. The mirror checks admission policies and, if approved, fetches the skill from upstream and caches it for future requests.
- **Admission policies** -- allow/deny rules that control which external skill slugs (and optionally which versions) may be proxied from upstream.
- **Pending requests** -- when a user requests an external skill that has no admission policy, the request is recorded so an admin can review and approve it later.

---

## Quickstart

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Steps

1. **Clone the repository**

   ```bash
   git clone <repository-url> clawhub-mirror
   cd clawhub-mirror
   ```

2. **Create a configuration file**

   ```bash
   cp config.example.yaml config.yaml
   ```

   Edit `config.yaml` to adjust settings as needed. The defaults work out of the box for local development with SQLite and local file storage.

3. **Install dependencies**

   ```bash
   uv sync
   ```

4. **Seed the database with an admin user and sample data**

   ```bash
   uv run python scripts/seed.py
   ```

   This creates three users (admin, publisher, reader) and a sample admission policy. Note the API tokens printed to the console.

5. **Start the server**

   ```bash
   uv run uvicorn clawhub_mirror.main:app --host 0.0.0.0 --port 8080
   ```

   The API is now available at `http://localhost:8080`. Visit `http://localhost:8080/docs` for the interactive Swagger UI.

---

## Docker

### Basic (SQLite + local storage)

```bash
docker compose up --build
```

This starts the application on port 8080. Mount your `config.yaml` into the container (the compose file expects it at `./config.yaml`).

### With MinIO (S3-compatible storage)

```bash
docker compose --profile s3 up --build
```

This additionally starts a MinIO instance on ports 9000 (API) and 9001 (console). Update your `config.yaml` to use S3 storage:

```yaml
storage:
  backend: "s3"
  s3_bucket: "clawhub-mirror"
  s3_endpoint_url: "http://minio:9000"
```

The MinIO console is available at `http://localhost:9001` (default credentials: `minioadmin` / `minioadmin`).

---

## Configuration Reference

Configuration is loaded from `config.yaml` (or the path specified by the `CLAWHUB_MIRROR_CONFIG` environment variable). All settings have sensible defaults for local development.

| Environment Variable | Config Key | Default | Description |
| --- | --- | --- | --- |
| `CLAWHUB_SERVER_HOST` | `server.host` | `0.0.0.0` | Address the server binds to |
| `CLAWHUB_SERVER_PORT` | `server.port` | `8080` | Port the server listens on |
| `CLAWHUB_SERVER_BASE_URL` | `server.base_url` | `http://localhost:8080` | Public base URL (used in discovery endpoint) |
| `CLAWHUB_DATABASE_URL` | `database.url` | `sqlite+aiosqlite:///./clawhub_mirror.db` | SQLAlchemy async database URL |
| `CLAWHUB_STORAGE_BACKEND` | `storage.backend` | `local` | Storage backend: `local` or `s3` |
| `CLAWHUB_STORAGE_LOCAL_PATH` | `storage.local_path` | `./skill_storage` | Directory for local file storage |
| `CLAWHUB_STORAGE_S3_BUCKET` | `storage.s3_bucket` | `clawhub-mirror-skills` | S3 bucket name |
| `CLAWHUB_STORAGE_S3_PREFIX` | `storage.s3_prefix` | `skills/` | Key prefix within the S3 bucket |
| `CLAWHUB_STORAGE_S3_ENDPOINT_URL` | `storage.s3_endpoint_url` | *(none)* | S3 endpoint URL (for MinIO or other S3-compatible services) |
| `CLAWHUB_STORAGE_S3_REGION` | `storage.s3_region` | `us-east-1` | AWS region for S3 |
| `CLAWHUB_UPSTREAM_URL` | `upstream.url` | `https://clawhub.ai` | Upstream ClawHub registry URL |
| `CLAWHUB_UPSTREAM_TIMEOUT` | `upstream.timeout` | `30` | Upstream request timeout in seconds |
| `CLAWHUB_AUTH_BOOTSTRAP_ADMIN_TOKEN` | `auth.bootstrap_admin_token` | `changeme-admin-token` | API token for the auto-created admin user |
| `CLAWHUB_AUTH_BOOTSTRAP_ADMIN_USERNAME` | `auth.bootstrap_admin_username` | `admin` | Username for the auto-created admin user |

---

## API Reference

All API endpoints are prefixed with `/api/v1` unless otherwise noted. Authentication uses Bearer tokens via the `Authorization` header:

```
Authorization: Bearer <api_token>
```

Roles: `admin` (full access), `publisher` (publish + read), `reader` (read only).

### Discovery and Health

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/.well-known/clawhub.json` | None | CLI discovery endpoint; returns `apiBase` URL |
| GET | `/healthz` | None | Health check; returns `{"status": "ok"}` |

### Skills

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/search` | None | Full-text search for skills (`?q=...&limit=20`) |
| GET | `/api/v1/skills` | None | List skills with cursor pagination (`?cursor=&limit=`) |
| GET | `/api/v1/skills/{slug}` | None | Get detailed information about a single skill |
| GET | `/api/v1/skills/{slug}/versions` | None | List all versions of a skill |
| GET | `/api/v1/resolve` | None | Resolve a skill version (`?slug=...&hash=...`) |
| GET | `/api/v1/download` | None | Download a skill zip (`?slug=...&version=...`) |
| POST | `/api/v1/skills` | admin, publisher | Publish a new skill version (multipart form upload) |
| DELETE | `/api/v1/skills/{slug}` | admin | Soft-delete a skill |

### Authentication

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/whoami` | Any | Returns the authenticated user's identity and role |

### Admin

All admin endpoints require the `admin` role.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/admin/users` | List all users |
| POST | `/api/v1/admin/users` | Create a new user (username, password, role) |
| DELETE | `/api/v1/admin/users/{username}` | Deactivate a user |
| GET | `/api/v1/admin/policies` | List all admission policies |
| POST | `/api/v1/admin/policies` | Create an admission policy |
| PUT | `/api/v1/admin/policies/{id}` | Update an admission policy |
| DELETE | `/api/v1/admin/policies/{id}` | Delete an admission policy |
| GET | `/api/v1/admin/policies/pending` | List pending (unapproved) skill requests |

---

## Admission Policy

The admission policy system controls which external skills from the upstream registry are allowed to pass through the mirror. This is the core governance mechanism for enterprise deployments.

### How it works

1. A user (or the CLI) requests a skill that does not exist locally (e.g., `clawhub install some-external-skill`).
2. The mirror checks the `admission_policies` table for a matching slug.
   - If an **allow** policy exists (and the version matches, if version-pinned), the skill is fetched from upstream, cached locally, and served to the user.
   - If a **deny** policy exists, the request is rejected with a 403 status.
   - If **no policy** exists, the request is recorded in the `pending_requests` table and the user receives a 403 indicating the skill needs administrator approval.
3. An administrator reviews the pending requests via `GET /api/v1/admin/policies/pending`.
4. The administrator creates an admission policy via `POST /api/v1/admin/policies`:

   ```json
   {
     "slug": "some-external-skill",
     "policy_type": "allow",
     "allowed_versions": null,
     "notes": "Reviewed and approved for internal use"
   }
   ```

   Setting `allowed_versions` to `null` permits all versions. To pin specific versions, provide a comma-separated string (e.g., `"1.0.0,1.1.0"`).

5. Subsequent requests for that skill are served transparently.

### Policy types

- **allow** -- permits the skill to be proxied from upstream. Optionally restricts to specific versions.
- **deny** -- explicitly blocks a skill, even if it exists upstream. Useful for known-bad or deprecated skills.

---

## CLI Integration

To point the ClawHub CLI at your mirror instance, set the `CLAWHUB_URL` environment variable:

```bash
export CLAWHUB_URL=http://localhost:8080
```

The CLI will discover the API base URL via the `/.well-known/clawhub.json` endpoint. All operations (search, install, resolve, publish) will then go through your mirror.

For authentication, set your API token:

```bash
export CLAWHUB_TOKEN=dev-admin-token
```

You can generate tokens for individual users through the admin API or by running the seed script.

---

## Development

### Running tests

```bash
uv run pytest
```

### Project structure

```
clawhub-mirror/
  src/clawhub_mirror/
    main.py           # FastAPI application entry point
    config.py         # Configuration loading (YAML + env vars)
    database.py       # SQLAlchemy async engine and session management
    models.py         # ORM models (User, Skill, SkillVersion, AdmissionPolicy)
    schemas.py        # Pydantic request/response schemas
    auth.py           # Authentication utilities and FastAPI dependencies
    storage.py        # Storage backends (local filesystem, S3)
    proxy.py          # Upstream proxy client
    routers/
      discovery.py    # /.well-known/clawhub.json and /healthz
      skills.py       # Skill CRUD, search, resolve, download
      admin.py        # User management and admission policies
      whoami.py       # /whoami endpoint
  scripts/
    seed.py           # Database seeding for development
  tests/              # Test suite
  config.example.yaml # Example configuration
  Dockerfile
  docker-compose.yml
  pyproject.toml
```

---

## License

See the LICENSE file for details.
