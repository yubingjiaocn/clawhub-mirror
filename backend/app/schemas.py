"""Pydantic schemas matching the ClawHub API response format."""

import json

from pydantic import BaseModel, Field


class VersionInfo(BaseModel):
    version: str
    created_at: int = Field(alias="createdAt")
    changelog: str | None = None
    model_config = {"populate_by_name": True}


class SkillStats(BaseModel):
    downloads: int = 0
    stars: int = 0


class OwnerInfo(BaseModel):
    handle: str
    display_name: str = Field(alias="displayName")
    model_config = {"populate_by_name": True}


class ResolveMatch(BaseModel):
    version: str


class ResolveResponse(BaseModel):
    match: ResolveMatch | None = None
    latest_version: VersionInfo | None = Field(None, alias="latestVersion")
    model_config = {"populate_by_name": True}


class SearchResultItem(BaseModel):
    slug: str
    display_name: str = Field(alias="displayName")
    summary: str | None = None
    version: str | None = None
    score: float = 0.0
    updated_at: int = Field(alias="updatedAt")
    model_config = {"populate_by_name": True}


class SearchResponse(BaseModel):
    results: list[SearchResultItem]


class SkillListItem(BaseModel):
    slug: str
    display_name: str = Field(alias="displayName")
    summary: str | None = None
    tags: list[str] = []
    stats: SkillStats = SkillStats()
    created_at: int = Field(alias="createdAt")
    updated_at: int = Field(alias="updatedAt")
    latest_version: VersionInfo | None = Field(None, alias="latestVersion")
    model_config = {"populate_by_name": True}


class SkillListResponse(BaseModel):
    items: list[SkillListItem]
    next_cursor: str | None = Field(None, alias="nextCursor")
    model_config = {"populate_by_name": True}


class SkillDetailResponse(BaseModel):
    skill: SkillListItem
    latest_version: VersionInfo | None = Field(None, alias="latestVersion")
    owner: OwnerInfo
    model_config = {"populate_by_name": True}


class SkillVersionsResponse(BaseModel):
    versions: list[VersionInfo]


class PublishResponse(BaseModel):
    slug: str
    version: str
    message: str = "Published successfully"


class WhoamiResponse(BaseModel):
    username: str
    role: str
    handle: str


class AdmissionPolicySchema(BaseModel):
    id: str
    slug: str
    allowed_versions: str | None = Field(None, alias="allowedVersions")
    policy_type: str = Field(alias="policyType")
    approved_by: str | None = Field(None, alias="approvedBy")
    approved_at: int | None = Field(None, alias="approvedAt")
    notes: str | None = None
    created_at: int = Field(alias="createdAt")
    model_config = {"populate_by_name": True}


class AdmissionPolicyListResponse(BaseModel):
    policies: list[AdmissionPolicySchema]


class PendingRequestSchema(BaseModel):
    id: str
    slug: str
    requested_by: str | None = Field(None, alias="requestedBy")
    requested_at: int | None = Field(None, alias="requestedAt")
    reason: str | None = None
    status: str
    model_config = {"populate_by_name": True}


class PendingRequestListResponse(BaseModel):
    requests: list[PendingRequestSchema]


class UserSchema(BaseModel):
    username: str
    role: str
    is_active: bool = Field(alias="isActive")
    created_at: int = Field(alias="createdAt")
    model_config = {"populate_by_name": True}


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "reader"


class UserCreateResponse(BaseModel):
    user: UserSchema
    api_token: str = Field(alias="apiToken")
    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class ProxySettingsRequest(BaseModel):
    enabled: bool
    upstream_url: str | None = None


class AdmissionPolicyCreateRequest(BaseModel):
    slug: str
    allowed_versions: str | None = None
    policy_type: str = "allow"
    notes: str | None = None


class AdmissionPolicyUpdateRequest(BaseModel):
    allowed_versions: str | None = None
    policy_type: str | None = None
    notes: str | None = None


def parse_tags(tags_str: str) -> list[str]:
    try:
        return json.loads(tags_str) if tags_str else []
    except Exception:
        return [t.strip() for t in tags_str.split(",") if t.strip()]


def normalize_tags(raw_tags: object) -> list[str]:
    """Normalize tags from various DynamoDB/upstream formats to a list of strings."""
    if isinstance(raw_tags, dict):
        return list(raw_tags.keys())
    if isinstance(raw_tags, str):
        return parse_tags(raw_tags)
    if raw_tags:
        return list(raw_tags)
    return []
