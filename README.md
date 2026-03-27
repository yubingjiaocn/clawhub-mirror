# ClawHub Mirror

Self-hosted [ClawHub](https://clawhub.ai)-compatible AgentSkill registry on AWS serverless. Drop-in replacement for the public ClawHub registry -- the standard [`clawhub`](https://docs.openclaw.ai/tools/clawhub) CLI and [`openclaw skills`](https://docs.openclaw.ai/cli#skills) commands work out of the box.

## Architecture

```
                  ┌──────────────────┐
                  │   CloudFront     │
                  │   (CDN)          │
                  └──┬───────────┬───┘
            /api/*   │           │   /*
         ┌───────────▼──┐   ┌───▼────────────┐
         │ API Gateway  │   │ S3 (frontend)  │
         │ (HTTP API)   │   │ React SPA      │
         └──────┬───────┘   └────────────────┘
                │
         ┌──────▼───────┐
         │   Lambda     │
         │ (FastAPI +   │
         │  Mangum)     │
         └──┬────────┬──┘
            │        │
     ┌──────▼──┐  ┌──▼────────┐
     │DynamoDB │  │ S3        │
     │(single  │  │ (skill    │
     │ table)  │  │  archives)│
     └─────────┘  └───────────┘
```

| Component | Technology |
|-----------|-----------|
| Compute | Lambda (Python 3.12), FastAPI + Mangum |
| Database | DynamoDB single-table design, 3 GSIs |
| Storage | S3 for skill zip archives |
| API | API Gateway HTTP API (v2) |
| CDN | CloudFront (S3 origin + API origin) |
| Frontend | React 19, Vite, Tailwind CSS v4 |
| IaC | Terraform with [terraform-aws-modules](https://registry.terraform.io/namespaces/terraform-aws-modules) |

## Quick Start

### Prerequisites

- AWS CLI configured with credentials
- Terraform >= 1.5
- Node.js >= 18 (for frontend build)
- Python 3.12+ (for backend development)

### 1. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform outputs:

| Output | Description |
|--------|-------------|
| `api_url` | API Gateway base URL |
| `cloudfront_distribution_domain` | CloudFront URL (frontend + API) |
| `dynamodb_table_name` | DynamoDB table name |
| `s3_bucket_name` | Skill archive S3 bucket |
| `frontend_bucket_name` | Frontend assets S3 bucket |
| `lambda_function_name` | Lambda function name |

### 2. Build and Deploy Frontend

```bash
cd frontend
npm install
npm run build

# Deploy to S3 (use bucket name from terraform output)
aws s3 sync dist/ s3://<frontend_bucket_name>/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id <cloudfront_distribution_id> \
  --paths "/*"
```

### 3. Seed Admin User

```bash
# Replace values from terraform output
python3 -c "
import boto3, bcrypt, secrets, time
ddb = boto3.resource('dynamodb', region_name='<region>')
table = ddb.Table('<dynamodb_table_name>')

password = 'your-secure-password'
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
token = secrets.token_urlsafe(32)

table.put_item(Item={
    'PK': 'USER#admin', 'SK': 'PROFILE',
    'username': 'admin',
    'hashedPassword': hashed,
    'role': 'admin',
    'apiToken': token,
    'isActive': True,
    'createdAt': int(time.time() * 1000),
    'GSI3PK': f'TOKEN#{token}',
    'GSI3SK': 'TOKEN',
})
print(f'Admin created. Password: {password}')
"
```

Or sign up from the web UI -- the first user can then be promoted to admin via DynamoDB.

### 4. Verify

```bash
# Check health
curl https://<cloudfront_domain>/healthz

# Open frontend
open https://<cloudfront_domain>
```

## Public ClawHub Proxy

The registry can optionally proxy requests to the public [ClawHub](https://clawhub.ai) registry. When enabled, skills not found locally are transparently fetched from upstream and cached in DynamoDB + S3.

### Enable/Disable

Toggle from the **Admin Dashboard** (web UI) or via the API:

```bash
# Enable proxy
curl -X PUT "$API_URL/api/v1/admin/settings/proxy" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Disable proxy
curl -X PUT "$API_URL/api/v1/admin/settings/proxy" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Check status
curl "$API_URL/api/v1/admin/settings/proxy" \
  -H "Authorization: Bearer <admin-token>"
```

### Behavior

| Scenario | Proxy Disabled | Proxy Enabled |
|----------|---------------|---------------|
| Search | Local results only | Local + upstream results (merged, deduped) |
| Install (local skill) | Served from DynamoDB/S3 | Same |
| Install (upstream skill) | 404 | Fetched from clawhub.ai, cached, served |
| Subsequent install | N/A | Served from cache (fast) |
| Disable after caching | Cached skills still available | -- |

### How Caching Works

- **Metadata**: Stored in DynamoDB with `isExternal=true` and `ownerUsername=__upstream__`
- **Archives**: Stored in S3 at `skills/{slug}/{version}.zip` on first download
- **Search**: Upstream results merged in real-time (not cached)
- **Timeout**: 10s per upstream request (within Lambda's 30s limit)
- **Failure handling**: Upstream errors are silently ignored; the registry degrades to local-only

## Terraform Configuration

### Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_name` | `clawhub` | Resource name prefix |
| `region` | `us-west-2` | AWS region |
| `environment` | `dev` | Environment tag (dev/staging/prod) |

### Multi-Region / Multi-Environment

S3 buckets use `bucket_prefix` (AWS-generated suffix) for global uniqueness. Lambda IAM roles include the region in their name. You can safely deploy multiple instances:

```bash
# Production in us-east-1
terraform apply -var="environment=prod" -var="region=us-east-1"

# Staging in eu-west-1
terraform apply -var="environment=staging" -var="region=eu-west-1"
```

### Terraform Modules

| Module | Version | Purpose |
|--------|---------|---------|
| `terraform-aws-modules/s3-bucket/aws` | ~> 5.0 | Skill archives + frontend assets |
| `terraform-aws-modules/lambda/aws` | ~> 8.0 | API compute |
| `terraform-aws-modules/apigateway-v2/aws` | ~> 6.0 | HTTP API |
| `terraform-aws-modules/cloudfront/aws` | ~> 6.0 | CDN with S3 + API origins |

## API Reference

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check (database + storage) |
| `GET` | `/.well-known/clawhub.json` | Registry discovery for CLI |
| `POST` | `/api/v1/auth/login` | Login (username/password -> session token) |
| `POST` | `/api/v1/auth/register` | Sign up (creates reader account) |
| `POST` | `/api/v1/auth/logout` | Invalidate session |

### Authenticated Endpoints (any role)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/whoami` | Current user info |
| `GET` | `/api/v1/skills` | List skills (paginated) |
| `GET` | `/api/v1/skills/:slug` | Skill detail |
| `GET` | `/api/v1/skills/:slug/versions` | Version history |
| `GET` | `/api/v1/resolve?slug=&hash=` | Version resolution |
| `GET` | `/api/v1/download?slug=&version=` | Download skill zip |
| `GET` | `/api/v1/search?q=&limit=` | Search skills |
| `GET` | `/api/v1/auth/keys` | List your API keys |
| `POST` | `/api/v1/auth/keys` | Generate API key |
| `DELETE` | `/api/v1/auth/keys/:keyId` | Revoke API key |

### Publisher Endpoints (admin or publisher role)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/skills` | Publish skill (multipart) |

### Admin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/admin/users` | Create user |
| `GET` | `/api/v1/admin/users` | List users |
| `DELETE` | `/api/v1/admin/users/:username` | Deactivate user |
| `GET/POST/PATCH/DELETE` | `/api/v1/admin/policies` | Admission policy CRUD |
| `GET` | `/api/v1/admin/policies/pending` | List pending requests |
| `POST` | `/api/v1/admin/policies/pending/:id/approve` | Approve request |
| `POST` | `/api/v1/admin/policies/pending/:id/deny` | Deny request |
| `DELETE` | `/api/v1/skills/:slug` | Soft-delete skill |

### Authentication

Two token types:

| Type | How to get | Use for |
|------|-----------|---------|
| **Session token** | `POST /api/v1/auth/login` | Frontend (browser), short-lived |
| **API key** | Settings page or `POST /api/v1/auth/keys` | CLI, CI/CD, programmatic access |

Both are sent as `Authorization: Bearer <token>`.

### Roles

| Role | Permissions |
|------|------------|
| `reader` | Browse, search, install skills |
| `publisher` | All reader permissions + publish skills |
| `admin` | All permissions + user management, policies, skill deletion |

## Development

### Backend

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt

# Run unit tests (moto-mocked, no AWS credentials needed)
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Local dev server (port 5173)
npm run build        # Production build
```

### Live API Tests (against deployed environment)

```bash
# 70 API tests covering all endpoints
CLAWHUB_ADMIN_USER=admin CLAWHUB_ADMIN_PASS=<password> \
  python3 -m pytest tests/test_live_api.py -v
```

### Playwright E2E Tests (browser tests against deployed frontend)

```bash
# 28 frontend tests
python3 -m venv .venv-test
.venv-test/bin/pip install playwright pytest pytest-playwright requests
.venv-test/bin/python -m playwright install chromium

CLAWHUB_FRONTEND_URL=https://<cloudfront_domain> \
CLAWHUB_ADMIN_USER=admin CLAWHUB_ADMIN_PASS=<password> \
  .venv-test/bin/python -m pytest tests/test_frontend.py -v --browser chromium
```

### Project Structure

```
clawhub-mirror/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Environment variable settings
│   │   ├── dynamodb.py          # DynamoDB single-table CRUD
│   │   ├── storage.py           # S3 operations
│   │   ├── auth.py              # Token auth + password hashing
│   │   ├── schemas.py           # Pydantic models (camelCase)
│   │   └── routers/
│   │       ├── auth.py          # Login, register, API keys
│   │       ├── skills.py        # Skill CRUD, search, download
│   │       ├── admin.py         # User + policy management
│   │       ├── discovery.py     # .well-known/clawhub.json
│   │       └── whoami.py        # Current user info
│   ├── tests/                   # Unit tests (moto mocks)
│   ├── handler.py               # Mangum Lambda entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/              # Page components
│   │   ├── components/          # Shared UI components
│   │   ├── lib/api.ts           # API client
│   │   └── main.tsx             # Router setup
│   ├── package.json
│   └── vite.config.ts
├── terraform/
│   ├── main.tf                  # Provider + locals
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Deployment outputs
│   ├── lambda.tf                # Lambda + IAM
│   ├── api_gateway.tf           # HTTP API
│   ├── dynamodb.tf              # Single table + GSIs
│   ├── s3.tf                    # Skill archive bucket
│   ├── frontend.tf              # Frontend bucket + OAC policy
│   └── cdn.tf                   # CloudFront distribution
├── tests/
│   ├── test_live_api.py         # 70 live API tests
│   └── test_frontend.py         # 28 Playwright E2E tests
└── README.md
```

### DynamoDB Single-Table Design

| Entity | PK | SK | GSIs |
|--------|----|----|------|
| User | `USER#{username}` | `PROFILE` | GSI3: `TOKEN#{apiToken}` |
| API Key | `USER#{username}` | `APIKEY#{keyId}` | GSI3: `TOKEN#{token}` |
| Session | `SESSION#{token}` | `META` | -- |
| Skill | `SKILL#{slug}` | `META` | GSI1: all skills by time, GSI2: by owner |
| Version | `SKILL#{slug}` | `VER#{version}` | -- |
| Policy | `POLICY#{slug}` | `META` | -- |
| Pending | `PENDING#{slug}` | `REQ#{timestamp}` | -- |

## License

MIT
