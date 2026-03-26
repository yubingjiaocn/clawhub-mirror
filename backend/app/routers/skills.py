"""Skill CRUD, search, resolve, and download endpoints."""

import re
import time
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response

from ..auth import get_current_user, require_role
from .. import dynamodb, storage
from ..schemas import (
    OwnerInfo,
    PublishResponse,
    ResolveMatch,
    ResolveResponse,
    SearchResponse,
    SearchResultItem,
    SkillDetailResponse,
    SkillListItem,
    SkillListResponse,
    SkillStats,
    SkillVersionsResponse,
    VersionInfo,
    parse_tags,
)

router = APIRouter(prefix="/api/v1", tags=["skills"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _skill_to_list_item(item: dict, versions: list[dict] | None = None) -> SkillListItem:
    """Convert a DynamoDB skill item to a SkillListItem schema."""
    if versions is None:
        versions = dynamodb.list_versions(item["slug"])
    versions_sorted = sorted(versions, key=lambda v: v.get("createdAt", 0), reverse=True)
    latest = versions_sorted[0] if versions_sorted else None
    tags = item.get("tags", [])
    if isinstance(tags, str):
        tags = parse_tags(tags)
    return SkillListItem(
        slug=item["slug"],
        displayName=item.get("displayName", item["slug"]),
        summary=item.get("summary"),
        tags=tags,
        stats=SkillStats(downloads=0),
        createdAt=item.get("createdAt", 0),
        updatedAt=item.get("updatedAt", 0),
        latestVersion=VersionInfo(
            version=latest["version"],
            createdAt=latest.get("createdAt", 0),
            changelog=latest.get("changelog"),
        ) if latest else None,
    )


# --- Resolve ---

@router.get("/resolve", response_model=ResolveResponse)
async def resolve_skill(
    slug: str = Query(..., description="Skill slug to resolve"),
    hash: Optional[str] = Query(None, description="Content hash to match"),
    user: dict = Depends(get_current_user),
) -> ResolveResponse:
    skill = dynamodb.get_skill(slug)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")

    versions = dynamodb.list_versions(slug)
    if not versions:
        return ResolveResponse(match=None, latestVersion=None)

    versions_sorted = sorted(versions, key=lambda v: v.get("createdAt", 0), reverse=True)
    latest = versions_sorted[0]

    match: ResolveMatch | None = None
    if hash:
        for v in versions_sorted:
            if v.get("storageKey") and hash in v["storageKey"]:
                match = ResolveMatch(version=v["version"])
                break

    return ResolveResponse(
        match=match,
        latestVersion=VersionInfo(
            version=latest["version"],
            createdAt=latest.get("createdAt", 0),
            changelog=latest.get("changelog"),
        ),
    )


# --- Download ---

@router.get("/download")
async def download_skill(
    slug: str = Query(..., description="Skill slug"),
    version: str = Query(..., description="Version string"),
    user: dict = Depends(get_current_user),
) -> Response:
    ver = dynamodb.get_version(slug, version)
    if not ver:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version}' not found for skill '{slug}'.",
        )

    data = storage.download(ver["storageKey"])
    if data is None:
        raise HTTPException(status_code=404, detail="Archive not found in storage.")

    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}-{version}.zip"',
        },
    )


# --- Search ---

@router.get("/search", response_model=SearchResponse)
async def search_skills(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> SearchResponse:
    items = dynamodb.search_skills(q, limit=limit)
    results = []
    for item in items:
        versions = dynamodb.list_versions(item["slug"])
        versions_sorted = sorted(versions, key=lambda v: v.get("createdAt", 0), reverse=True)
        latest = versions_sorted[0] if versions_sorted else None
        results.append(SearchResultItem(
            slug=item["slug"],
            displayName=item.get("displayName", item["slug"]),
            summary=item.get("summary"),
            version=latest["version"] if latest else None,
            score=1.0,
            updatedAt=item.get("updatedAt", 0),
        ))
    return SearchResponse(results=results)


# --- List skills ---

@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> SkillListResponse:
    items, next_cursor = dynamodb.list_skills(limit=limit, cursor=cursor)
    return SkillListResponse(
        items=[_skill_to_list_item(item) for item in items],
        nextCursor=next_cursor,
    )


# --- Skill detail ---

@router.get("/skills/{slug}", response_model=SkillDetailResponse)
async def get_skill(
    slug: str,
    user: dict = Depends(get_current_user),
) -> SkillDetailResponse:
    skill = dynamodb.get_skill(slug)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")

    versions = dynamodb.list_versions(slug)
    versions_sorted = sorted(versions, key=lambda v: v.get("createdAt", 0), reverse=True)
    latest = versions_sorted[0] if versions_sorted else None

    owner_username = skill.get("ownerUsername", "unknown")
    tags = skill.get("tags", [])
    if isinstance(tags, str):
        tags = parse_tags(tags)

    return SkillDetailResponse(
        skill=SkillListItem(
            slug=skill["slug"],
            displayName=skill.get("displayName", slug),
            summary=skill.get("summary"),
            tags=tags,
            stats=SkillStats(downloads=0),
            createdAt=skill.get("createdAt", 0),
            updatedAt=skill.get("updatedAt", 0),
            latestVersion=VersionInfo(
                version=latest["version"],
                createdAt=latest.get("createdAt", 0),
                changelog=latest.get("changelog"),
            ) if latest else None,
        ),
        latestVersion=VersionInfo(
            version=latest["version"],
            createdAt=latest.get("createdAt", 0),
            changelog=latest.get("changelog"),
        ) if latest else None,
        owner=OwnerInfo(
            handle=owner_username,
            displayName=owner_username,
        ),
    )


# --- Skill versions ---

@router.get("/skills/{slug}/versions", response_model=SkillVersionsResponse)
async def get_skill_versions(
    slug: str,
    user: dict = Depends(get_current_user),
) -> SkillVersionsResponse:
    skill = dynamodb.get_skill(slug)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")

    versions = dynamodb.list_versions(slug)
    versions_sorted = sorted(versions, key=lambda v: v.get("createdAt", 0), reverse=True)

    return SkillVersionsResponse(
        versions=[
            VersionInfo(
                version=v["version"],
                createdAt=v.get("createdAt", 0),
                changelog=v.get("changelog"),
            )
            for v in versions_sorted
        ]
    )


# --- Publish ---

@router.post("/skills", response_model=PublishResponse)
async def publish_skill(
    slug: str = Form(..., description="Unique skill slug"),
    version: str = Form(..., description="Semantic version string"),
    display_name: Optional[str] = Form(None, description="Human-readable name"),
    summary: Optional[str] = Form(None, description="Short description"),
    changelog: Optional[str] = Form(None, description="Version changelog"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    file: UploadFile = File(..., description="Skill zip archive"),
    user: dict = Depends(require_role("admin", "publisher")),
) -> PublishResponse:
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must be lowercase alphanumeric with hyphens only.",
        )

    zip_data = await file.read()
    if not zip_data:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    storage_key = f"skills/{slug}/{version}.zip"

    # Check for duplicate version
    existing_version = dynamodb.get_version(slug, version)
    if existing_version:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version} already exists for {slug}.",
        )

    tag_list: list[str] = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Get or create skill
    existing_skill = dynamodb.get_skill(slug)
    username = user["username"]

    if existing_skill:
        updates: dict = {"updatedAt": _now_ms()}
        if display_name:
            updates["displayName"] = display_name
        if summary is not None:
            updates["summary"] = summary
        if tags is not None:
            updates["tags"] = tag_list
        dynamodb.update_skill(slug, **updates)
    else:
        dynamodb.put_skill(
            slug=slug,
            display_name=display_name or slug,
            summary=summary or "",
            tags=tag_list,
            owner_username=username,
        )

    # Upload zip to S3
    storage.upload(storage_key, zip_data)

    # Create version record
    dynamodb.put_version(
        slug=slug,
        version=version,
        changelog=changelog or "",
        storage_key=storage_key,
        file_size=len(zip_data),
    )

    return PublishResponse(slug=slug, version=version)


# --- Delete (soft) ---

@router.delete("/skills/{slug}", status_code=200)
async def delete_skill(
    slug: str,
    user: dict = Depends(require_role("admin")),
) -> dict:
    skill = dynamodb.get_skill(slug)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")

    dynamodb.soft_delete_skill(slug)
    return {"message": "Skill deleted"}
