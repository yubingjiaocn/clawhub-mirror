# ClawHub Enterprise - Implementation Plan

## Overview
Self-hosted ClawHub-compatible skill registry on AWS serverless stack.
CLI-compatible with `clawhub` CLI (`CLAWHUB_URL` override).

## Architecture
- **API**: API Gateway (REST) + Lambda (Python 3.12, FastAPI + Mangum)
- **Database**: DynamoDB single-table design
- **Storage**: S3 for skill zip archives
- **Frontend**: React SPA on S3 + CloudFront (Phase 2)
- **Auth**: API key (Bearer token) in V1, Cognito + GitHub OAuth in V2
- **IaC**: Terraform with modules
- **Search**: DDB scan + contains filter V1, Bedrock embedding V2

## DynamoDB Single-Table Design

### Primary Key: PK (String) + SK (String)

| Entity | PK | SK | Attributes |
|---|---|---|---|
| Skill | `SKILL#<slug>` | `META` | displayName, summary, tags, ownerUsername, readme, isDeleted, isExternal, createdAt, updatedAt |
| SkillVersion | `SKILL#<slug>` | `VER#<version>` | changelog, storageKey, fileSize, createdAt |
| User | `USER#<username>` | `PROFILE` | hashedPassword, role, apiToken, isActive, createdAt |
| AdmissionPolicy | `POLICY#<slug>` | `META` | allowedVersions, policyType, approvedBy, approvedAt, notes, createdAt |
| PendingRequest | `PENDING#<slug>` | `REQ#<timestamp>` | requestedBy, reason, status |

### GSIs

| GSI | PK | SK | Purpose |
|---|---|---|---|
| GSI1 | `GSI1PK` = `ALL_SKILLS` | `GSI1SK` = `<updatedAt>#<slug>` | List all skills, sorted by updated_at |
| GSI2 | `GSI2PK` = `OWNER#<username>` | `GSI2SK` = `<updatedAt>#<slug>` | List skills by owner |
| GSI3 | `GSI3PK` = `TOKEN#<apiToken>` | `GSI3SK` = `TOKEN` | Token-based auth lookup |

## API Endpoints (ClawHub-compatible)

### Discovery
- `GET /.well-known/clawhub.json` → registry metadata

### Skills CRUD
- `GET /api/v1/skills` → list skills (paginated)
- `GET /api/v1/skills/{slug}` → skill detail
- `GET /api/v1/skills/{slug}/versions` → version list
- `POST /api/v1/skills` → publish (multipart upload)
- `DELETE /api/v1/skills/{slug}` → soft delete

### Resolution & Download
- `GET /api/v1/resolve?slug=xxx` → version resolution
- `GET /api/v1/download?slug=xxx&version=yyy` → download zip

### Search
- `GET /api/v1/search?q=xxx` → full-text search

### Auth
- `GET /api/v1/whoami` → current user info

### Admin (enterprise features)
- `GET /api/v1/admin/policies` → list admission policies
- `POST /api/v1/admin/policies` → create policy
- `PATCH /api/v1/admin/policies/{slug}` → update policy
- `DELETE /api/v1/admin/policies/{slug}` → delete policy
- `GET /api/v1/admin/policies/pending` → pending requests
- `POST /api/v1/admin/policies/pending/{id}/approve` → approve
- `POST /api/v1/admin/policies/pending/{id}/deny` → deny
- `POST /api/v1/admin/users` → create user
- `GET /api/v1/admin/users` → list users

### Health
- `GET /healthz` → health check

## Terraform Modules

### `modules/database`
- DynamoDB table with GSIs
- On-demand billing (pay-per-request)

### `modules/storage`
- S3 bucket for skill archives
- Lifecycle rules, versioning, encryption

### `modules/api`
- Lambda function (Python 3.12)
- API Gateway REST API
- IAM roles (Lambda → DDB + S3)
- Lambda layer for dependencies

### `modules/cdn` (Phase 2)
- S3 bucket for frontend static files
- CloudFront distribution
- OAC for S3 access

## Reference Code
- Existing clawhub-mirror: `/home/ubuntu/clawhub-mirror/` (FastAPI, SQLAlchemy, ~2800 lines)
- ClawHub source: `https://github.com/openclaw/clawhub` (Convex + TanStack Start)

## Phases
1. **Phase 1**: Terraform infra + Backend API (DDB + S3 + Lambda) — all ClawHub CLI compatible endpoints
2. **Phase 2**: Frontend SPA (React, deploy to CloudFront)
3. **Phase 3**: Upstream proxy/mirror mode, enhanced search (Bedrock embeddings)
