# ClawHub Mirror

Self-hosted [ClawHub](https://clawhub.ai)-compatible skill registry on AWS serverless.

Drop-in replacement for the public ClawHub registry — point `CLAWHUB_URL` at your deployment and the standard `clawhub` CLI works out of the box.

## Architecture

```
┌─────────────┐     ┌───────────────┐     ┌──────────┐
│  clawhub    │────▶│ API Gateway   │────▶│  Lambda  │
│  CLI        │     │ (HTTP API)    │     │ (FastAPI)│
└─────────────┘     └───────────────┘     └────┬─────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │                     │
                              ┌─────▼─────┐        ┌─────▼─────┐
                              │ DynamoDB  │        │    S3     │
                              │(single-   │        │(skill     │
                              │ table)    │        │ archives) │
                              └───────────┘        └───────────┘
```

- **Compute**: Lambda (Python 3.12) with FastAPI + Mangum
- **Database**: DynamoDB single-table design with 3 GSIs
- **Storage**: S3 for skill zip archives
- **API**: API Gateway HTTP API (v2)
- **IaC**: Terraform with [terraform-aws-modules](https://registry.terraform.io/namespaces/terraform-aws-modules)

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5
- Python 3.12+

### Deploy

```bash
# Build Lambda package
chmod +x scripts/build-lambda.sh
./scripts/build-lambda.sh

# Deploy infrastructure
cd terraform
terraform init
terraform plan
terraform apply
```

### Configure CLI

```bash
export CLAWHUB_URL=<api_gateway_url_from_terraform_output>
export CLAWHUB_TOKEN=<your_admin_api_token>

# Verify
clawhub search "my-skill"
```

### Create First Admin User

After deployment, use the seed script or invoke the Lambda directly:

```bash
# Via curl
curl -X POST "$CLAWHUB_URL/api/v1/admin/users" \
  -H "Authorization: Bearer <bootstrap_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme", "role": "admin"}'
```

## API Compatibility

Full [ClawHub CLI](https://docs.openclaw.ai/tools/clawhub) compatibility:

| Endpoint | Description |
|---|---|
| `GET /.well-known/clawhub.json` | Registry discovery |
| `GET /api/v1/resolve` | Version resolution |
| `GET /api/v1/download` | Download skill zip |
| `GET /api/v1/search` | Search skills |
| `GET /api/v1/skills` | List skills (paginated) |
| `GET /api/v1/skills/:slug` | Skill detail |
| `GET /api/v1/skills/:slug/versions` | Version history |
| `POST /api/v1/skills` | Publish (multipart upload) |
| `DELETE /api/v1/skills/:slug` | Soft delete |
| `GET /api/v1/whoami` | Current user info |
| `GET /healthz` | Health check |

### Enterprise Features

| Endpoint | Description |
|---|---|
| `POST /api/v1/admin/users` | Create user (admin/publisher/reader roles) |
| `GET /api/v1/admin/users` | List users |
| `*/api/v1/admin/policies` | Admission policy CRUD |
| `*/api/v1/admin/policies/pending` | Pending request approve/deny |

## Terraform Modules

| Module | Version | Purpose |
|---|---|---|
| `terraform-aws-modules/dynamodb-table/aws` | ~> 5.0 | Single-table with 3 GSIs |
| `terraform-aws-modules/s3-bucket/aws` | ~> 5.0 | Skill archive storage |
| `terraform-aws-modules/lambda/aws` | ~> 8.0 | API compute |
| `terraform-aws-modules/apigateway-v2/aws` | ~> 6.0 | HTTP API |

## Development

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt

# Run tests (moto mocks, no AWS needed)
pytest tests/ -v
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── config.py         # Env var settings
│   │   ├── dynamodb.py       # DDB single-table CRUD
│   │   ├── storage.py        # S3 operations
│   │   ├── auth.py           # Bearer token auth
│   │   ├── schemas.py        # Pydantic models (camelCase)
│   │   └── routers/          # API endpoints
│   ├── tests/                # 22 tests with moto mocks
│   ├── handler.py            # Mangum Lambda entry point
│   └── requirements.txt
├── terraform/                # IaC (community modules)
├── scripts/
│   └── build-lambda.sh       # Package Lambda zip
└── PLAN.md                   # Design doc
```

## License

MIT
