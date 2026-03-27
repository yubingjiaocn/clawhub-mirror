# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Self-hosted ClawHub-compatible skill registry on AWS serverless. Drop-in replacement for the public ClawHub registry — the standard `clawhub` CLI works against this deployment when `CLAWHUB_SITE` is set.

## Production Environment

- **API Gateway**: `https://3z258qsqrf.execute-api.us-west-2.amazonaws.com`
- **CloudFront**: `https://d1gta4s2b4m2k6.cloudfront.net`
- **Region**: `us-west-2`
- **Lambda**: `clawhub-dev-api`
- **DynamoDB table**: `clawhub-dev`
- **S3 bucket**: `clawhub-dev-skills-*`
- **SSH to host**: `ssh -p 6222 ubuntu@52.33.239.78`

The admin user was seeded via Terraform (`admin` / `changeme123`) but the password hash may be SHA-256 (if bcrypt wasn't available during `terraform apply`). If admin login fails, register a new user via `/api/v1/auth/register` or re-seed the admin with bcrypt.

## Commands

### Backend (Python 3.12, FastAPI)

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt

# Run all tests (moto-mocked, no AWS credentials needed)
pytest tests/ -v

# Run a single test file or test
pytest tests/test_skills.py -v
pytest tests/test_skills.py::test_publish_skill -v
```

Note: `python-multipart` is required for publish endpoint tests. The test `test_well_known_returns_api_base` has a pre-existing failure (test expects `/api/v1` suffix but the discovery endpoint returns the base URL without it).

### Frontend (React 19, Vite, Tailwind v4)

```bash
cd frontend
npm install
npm run dev      # local dev server
npm run build    # production build (tsc + vite)
npm test         # run unit tests (vitest)
npm run test:watch  # watch mode
```

### E2E & Live API Tests (root `tests/` directory)

These run against the **live deployed environment** (not mocked). Requires `playwright`, `requests`, and `pytest-playwright`.

```bash
# Live API tests (requests-based, no browser needed)
pip install requests pytest
pytest tests/test_live_api.py -v

# Frontend E2E tests (Playwright, needs browser)
pip install pytest-playwright
playwright install chromium
pytest tests/test_frontend.py -v

# Override target environment
CLAWHUB_API_BASE=https://... pytest tests/test_live_api.py -v
CLAWHUB_FRONTEND_URL=https://... pytest tests/test_frontend.py -v
```

Note: Live tests expect an admin user. Set `CLAWHUB_ADMIN_USER` / `CLAWHUB_ADMIN_PASS` or `CLAWHUB_ADMIN_TOKEN` env vars.

### Lambda Deployment Package

```bash
./scripts/build-lambda.sh   # outputs build/lambda.zip
```

### Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Architecture

**Backend**: FastAPI app wrapped by Mangum for Lambda. Entry point is `backend/handler.py` → `app.main.create_app()`. Routers are split by domain: `skills`, `admin`, `discovery`, `whoami`, `auth`.

**Database**: DynamoDB single-table design. All entities (Skill, SkillVersion, User, ApiKey, Session, AdmissionPolicy, PendingRequest, SystemSettings) share one table with `PK`/`SK` composite keys. Three GSIs: GSI1 (all skills by updatedAt), GSI2 (skills by owner), GSI3 (token-based auth lookup). All CRUD lives in `backend/app/dynamodb.py` which uses module-level singletons (`_table`, `_client`) that tests reset between runs.

**Storage**: S3 for skill zip archives, abstracted in `backend/app/storage.py`.

**Auth**: Bearer token auth via GSI3 lookup. Supports both API tokens (on user profile) and API keys (separate APIKEY# items) and session tokens (from login). Roles: admin, publisher, reader. Logic in `backend/app/auth.py`. Role constants (`ADMIN`, `PUBLISHER`, `READER`) are defined there but not yet used across the codebase.

**Upstream Proxy**: Optional passthrough to the public ClawHub registry (`backend/app/upstream.py`). When enabled via admin settings, skills not found locally are fetched from upstream and cached. `is_proxy_enabled()` is a sync function that reads the proxy setting from DynamoDB.

**API**: Full ClawHub CLI compatibility — discovery (`/.well-known/clawhub.json`), skills CRUD, version resolution, search (DDB scan + contains filter in V1), admin endpoints for users, admission policies, and proxy settings.

**Frontend**: React SPA with react-router-dom, Tailwind CSS v4. Routes: Home, Skills, SkillDetail, Search, Publish, Admin, Settings, Guide, ApiReference.

**IaC**: Terraform using community modules (`terraform-aws-modules/*`) for DynamoDB, S3, Lambda, API Gateway v2, and CloudFront CDN. Admin user is seeded via `seed.tf` on first deploy.

## Key Conventions

- Backend schemas use **camelCase** field names (matching DynamoDB attribute names) via Pydantic models in `backend/app/schemas.py`.
- Shared helpers: `normalize_tags()` in schemas.py for tag format normalization; `_build_update_expression()` in dynamodb.py for DynamoDB SET expressions; `_sort_versions()`, `_make_version_info()`, `_skill_to_list_item()` in skills.py; `_make_policy_schema()` in admin.py. Prefer using these over inline duplication.
- Config is env-var driven (`TABLE_NAME`, `BUCKET_NAME`, `REGION`, `ENVIRONMENT`, `CORS_ORIGINS`) — see `backend/app/config.py`.
- Tests use `moto`'s `mock_aws` context manager. The `conftest.py` sets env vars **before** app imports and resets DynamoDB/S3 singletons between tests.
- Pending request IDs use composite format `slug::timestamp`.
- Frontend API client (`frontend/src/lib/api.ts`) provides typed `get()`, `post()`, `del()` helpers — use them instead of raw `fetch()` for API calls.
