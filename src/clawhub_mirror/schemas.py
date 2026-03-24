"""Pydantic schemas matching the ClawHub API response format."""

from pydantic import BaseModel, Field


# Shared
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


# Resolve
class ResolveMatch(BaseModel):
    version: str


class ResolveResponse(BaseModel):
    match: ResolveMatch | None = None
    latest_version: VersionInfo | None = Field(None, alias="latestVersion")
    model_config = {"populate_by_name": True}


# Search
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


# Skills list
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


# Skill detail
class SkillDetailResponse(BaseModel):
    skill: SkillListItem  # reuse, has same fields
    latest_version: VersionInfo | None = Field(None, alias="latestVersion")
    owner: OwnerInfo
    model_config = {"populate_by_name": True}


# Skill versions list
class SkillVersionsResponse(BaseModel):
    versions: list[VersionInfo]


# Publish response
class PublishResponse(BaseModel):
    slug: str
    version: str
    message: str = "Published successfully"


# Whoami
class WhoamiResponse(BaseModel):
    username: str
    role: str
    handle: str


# Admin - Admission Policy
class AdmissionPolicySchema(BaseModel):
    id: int
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
    id: int
    slug: str
    requested_by: str | None = Field(None, alias="requestedBy")
    requested_at: int = Field(None, alias="requestedAt")
    reason: str | None = None
    status: str
    model_config = {"populate_by_name": True}


class PendingRequestListResponse(BaseModel):
    requests: list[PendingRequestSchema]


# Admin - User management
class UserSchema(BaseModel):
    id: int
    username: str
    role: str
    api_token: str | None = Field(None, alias="api_token")
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


# Error
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


# Admission policy create/update
class AdmissionPolicyCreateRequest(BaseModel):
    slug: str
    allowed_versions: str | None = None
    policy_type: str = "allow"
    notes: str | None = None


class AdmissionPolicyUpdateRequest(BaseModel):
    allowed_versions: str | None = None
    policy_type: str | None = None
    notes: str | None = None

# Aliases for backward compat with routers
SkillDetail = SkillListItem

class VersionListResponse(BaseModel):
    items: list[VersionInfo]
    next_cursor: str | None = Field(None, alias="nextCursor")
    model_config = {"populate_by_name": True}

def parse_tags(tags_str: str) -> list[str]:
    """Parse tags from JSON string or comma-separated string."""
    import json
    try:
        return json.loads(tags_str) if tags_str else []
    except Exception:
        return [t.strip() for t in tags_str.split(",") if t.strip()]

def skill_to_list_item(skill) -> "SkillListItem":
    """Convert a Skill ORM object to a SkillListItem schema."""
    sorted_versions = sorted(skill.versions, key=lambda v: v.created_at, reverse=True)
    latest = sorted_versions[0] if sorted_versions else None
    tags = skill.tags if isinstance(skill.tags, list) else parse_tags(skill.tags or "")
    return SkillListItem(
        slug=skill.slug,
        displayName=skill.display_name,
        summary=skill.summary,
        tags=tags,
        stats=SkillStats(downloads=0),
        createdAt=skill.created_at,
        updatedAt=skill.updated_at,
        latestVersion=VersionInfo(
            version=latest.version,
            createdAt=latest.created_at,
            changelog=latest.changelog,
        ) if latest else None,
    )
