"""Skill CRUD, search, resolve, and download endpoints."""

from __future__ import annotations

import hashlib
import json
import logging
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
    Request,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_current_user, require_role
from ..database import get_session
from ..models import AdmissionPolicy, PendingRequest, Skill, SkillVersion, User
from ..proxy import UpstreamProxy
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
    skill_to_list_item,
)
from ..storage import StorageBackend

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["skills"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def _now_ms() -> int:
    """Current time as Unix epoch milliseconds."""
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eager_skill():
    """Base select for Skill with eagerly-loaded relationships."""
    return select(Skill).options(
        selectinload(Skill.versions),
        selectinload(Skill.owner),
    )


async def _get_skill_or_404(
    slug: str,
    db: AsyncSession,
    *,
    allow_deleted: bool = False,
) -> Skill:
    """Fetch a skill by slug or raise 404."""
    query = _eager_skill().where(Skill.slug == slug)
    if not allow_deleted:
        query = query.where(Skill.is_deleted.is_(False))
    result = await db.execute(query)
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")
    return skill


async def _check_admission(
    slug: str,
    version: Optional[str],
    db: AsyncSession,
) -> bool:
    """Check whether an external skill slug is admitted by policy.

    Returns False if there is an explicit deny policy or no allow policy exists.
    When an allow policy specifies allowed_versions, the requested version must
    be in that comma-separated list.
    """
    # Check for explicit deny first
    result = await db.execute(
        select(AdmissionPolicy).where(
            AdmissionPolicy.slug == slug,
            AdmissionPolicy.policy_type == "deny",
        )
    )
    if result.scalar_one_or_none():
        return False

    # Check for allow policy
    result = await db.execute(
        select(AdmissionPolicy).where(
            AdmissionPolicy.slug == slug,
            AdmissionPolicy.policy_type == "allow",
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        return False

    # If version-pinned, check the version
    if policy.allowed_versions and version:
        allowed = {v.strip() for v in policy.allowed_versions.split(",")}
        return version in allowed

    return True


async def _record_pending(
    slug: str,
    username: Optional[str],
    db: AsyncSession,
) -> None:
    """Record a pending request for an unapproved external skill."""
    existing = await db.execute(
        select(PendingRequest).where(PendingRequest.slug == slug)
    )
    if not existing.scalar_one_or_none():
        db.add(PendingRequest(slug=slug, requested_by=username, status="pending"))
        await db.commit()


def _sort_versions(versions: list[SkillVersion]) -> list[SkillVersion]:
    """Sort versions by created_at descending so index 0 is latest."""
    return sorted(versions, key=lambda v: v.created_at, reverse=True)


# ---------------------------------------------------------------------------
# Resolve
# ---------------------------------------------------------------------------

@router.get("/resolve", response_model=ResolveResponse)
async def resolve_skill(
    request: Request,
    slug: str = Query(..., description="Skill slug to resolve"),
    hash: Optional[str] = Query(None, description="Content hash to match a version"),
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
) -> ResolveResponse:
    """Resolve a skill version by slug and optional content hash.

    Looks up the skill locally first. If not found, checks admission policy
    and proxies to upstream if allowed. Returns 403 if not in the whitelist.
    """
    # Try local first
    result = await db.execute(
        _eager_skill().where(Skill.slug == slug, Skill.is_deleted.is_(False))
    )
    skill = result.scalar_one_or_none()

    if skill and skill.versions:
        sorted_versions = _sort_versions(list(skill.versions))
        latest = sorted_versions[0]
        match: ResolveMatch | None = None
        if hash:
            for v in sorted_versions:
                if v.storage_key and hash in v.storage_key:
                    match = ResolveMatch(version=v.version)
                    break
        return ResolveResponse(
            match=match,
            latestVersion=VersionInfo(
                version=latest.version,
                createdAt=latest.created_at,
                changelog=latest.changelog,
            ),
        )

    # Try upstream proxy
    if await _check_admission(slug, None, db):
        proxy: UpstreamProxy = request.app.state.proxy
        upstream_data = await proxy.resolve(slug, hash)
        if upstream_data:
            return ResolveResponse(**upstream_data)

    # Not admitted -- record as pending and return 403
    if not skill:
        await _record_pending(slug, user.username if user else "anonymous", db)
        raise HTTPException(
            status_code=403,
            detail=f"Skill '{slug}' is not in the whitelist. "
            "An administrator must approve it before it can be resolved.",
        )

    return ResolveResponse(match=None, latestVersion=None)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

@router.get("/download")
async def download_skill(
    request: Request,
    slug: str = Query(..., description="Skill slug"),
    version: str = Query(..., description="Version string"),
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
) -> Response:
    """Download a skill zip file.

    Serves from local storage first. If not found locally, checks admission
    policy and proxies the download from upstream. Returns 403 if not admitted,
    404 if not found anywhere.
    """
    storage: StorageBackend = request.app.state.storage

    # Look up local version
    result = await db.execute(
        _eager_skill().where(Skill.slug == slug, Skill.is_deleted.is_(False))
    )
    skill = result.scalar_one_or_none()

    if skill:
        for v in skill.versions:
            if v.version == version:
                data = await storage.download(v.storage_key)
                if data:
                    return Response(
                        content=data,
                        media_type="application/zip",
                        headers={
                            "Content-Disposition": (
                                f'attachment; filename="{slug}-{version}.zip"'
                            ),
                        },
                    )

    # Try upstream
    if await _check_admission(slug, version, db):
        proxy: UpstreamProxy = request.app.state.proxy
        zip_data = await proxy.download(slug, version)
        if zip_data:
            # Cache locally for future requests
            storage_key = f"skills/{slug}/{version}.zip"
            await storage.upload(storage_key, zip_data)

            # Upsert skill + version in DB for future local resolution
            if not skill:
                skill = Skill(
                    slug=slug,
                    display_name=slug,
                    is_external=True,
                    owner_id=user.id,
                )
                db.add(skill)
                await db.flush()

            db.add(
                SkillVersion(
                    skill_id=skill.id,
                    version=version,
                    storage_key=storage_key,
                    file_size=len(zip_data),
                )
            )
            skill.updated_at = _now_ms()
            await db.commit()

            return Response(
                content=zip_data,
                media_type="application/zip",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{slug}-{version}.zip"'
                    ),
                },
            )

    # Not admitted or not found
    if not skill:
        await _record_pending(slug, user.username if user else "anonymous", db)
        raise HTTPException(
            status_code=403,
            detail=f"Skill '{slug}' is not in the whitelist. "
            "An administrator must approve it before it can be downloaded.",
        )

    raise HTTPException(
        status_code=404,
        detail=f"Version '{version}' not found for skill '{slug}'.",
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search", response_model=SearchResponse)
async def search_skills(
    q: str = Query("", description="Full-text search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
) -> SearchResponse:
    """Search skills using FTS5 full-text search.

    Uses the skill_fts virtual table for ranked results. Falls back to LIKE
    queries if FTS5 is unavailable or the query is empty.
    """
    if not q.strip():
        # Return latest skills when no query provided
        result = await db.execute(
            _eager_skill()
            .where(Skill.is_deleted.is_(False))
            .order_by(Skill.updated_at.desc())
            .limit(limit)
        )
        skills = result.scalars().unique().all()
        return SearchResponse(
            results=[
                SearchResultItem(
                    slug=s.slug,
                    displayName=s.display_name,
                    summary=s.summary,
                    version=(
                        _sort_versions(list(s.versions))[0].version
                        if s.versions
                        else None
                    ),
                    score=1.0,
                    updatedAt=s.updated_at,
                )
                for s in skills
            ]
        )

    # FTS5 search
    try:
        safe_q = q.replace('"', '""')
        fts_query = text(
            "SELECT rowid, rank FROM skill_fts "
            "WHERE skill_fts MATCH :q ORDER BY rank LIMIT :limit"
        )
        fts_result = await db.execute(
            fts_query, {"q": f'"{safe_q}"', "limit": limit}
        )
        rows = fts_result.fetchall()

        if rows:
            ids = [r[0] for r in rows]
            ranks = {r[0]: r[1] for r in rows}
            result = await db.execute(
                _eager_skill().where(
                    Skill.id.in_(ids), Skill.is_deleted.is_(False)
                )
            )
            skills = result.scalars().unique().all()
            return SearchResponse(
                results=[
                    SearchResultItem(
                        slug=s.slug,
                        displayName=s.display_name,
                        summary=s.summary,
                        version=(
                            _sort_versions(list(s.versions))[0].version
                            if s.versions
                            else None
                        ),
                        score=abs(ranks.get(s.id, 0)),
                        updatedAt=s.updated_at,
                    )
                    for s in skills
                ]
            )
    except Exception:
        logger.debug("FTS5 search failed, falling back to LIKE", exc_info=True)

    # Fallback: LIKE search
    pattern = f"%{q}%"
    result = await db.execute(
        _eager_skill()
        .where(
            Skill.is_deleted.is_(False),
            (Skill.slug.ilike(pattern))
            | (Skill.display_name.ilike(pattern))
            | (Skill.summary.ilike(pattern)),
        )
        .limit(limit)
    )
    skills = result.scalars().unique().all()
    return SearchResponse(
        results=[
            SearchResultItem(
                slug=s.slug,
                displayName=s.display_name,
                summary=s.summary,
                version=(
                    _sort_versions(list(s.versions))[0].version
                    if s.versions
                    else None
                ),
                score=1.0,
                updatedAt=s.updated_at,
            )
            for s in skills
        ]
    )


# ---------------------------------------------------------------------------
# List skills
# ---------------------------------------------------------------------------

@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    cursor: Optional[str] = Query(
        None, description="Cursor (updated_at of last item) for pagination"
    ),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SkillListResponse:
    """List skills with cursor-based pagination.

    Skills are ordered by updated_at descending. The cursor is the updated_at
    value of the last item on the previous page.
    """
    query = (
        _eager_skill()
        .where(Skill.is_deleted.is_(False))
        .order_by(Skill.updated_at.desc())
    )

    if cursor:
        try:
            cursor_ts = int(cursor)
            query = query.where(Skill.updated_at < cursor_ts)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid cursor value."
            )

    query = query.limit(limit + 1)
    result = await db.execute(query)
    skills = list(result.scalars().unique().all())

    next_cursor: Optional[str] = None
    if len(skills) > limit:
        skills = skills[:limit]
        next_cursor = str(skills[-1].updated_at)

    return SkillListResponse(
        items=[skill_to_list_item(s) for s in skills],
        nextCursor=next_cursor,
    )


# ---------------------------------------------------------------------------
# Skill detail
# ---------------------------------------------------------------------------

@router.get("/skills/{slug}", response_model=SkillDetailResponse)
async def get_skill(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
) -> SkillDetailResponse:
    """Get detailed information about a single skill.

    If not found locally, attempts upstream lookup for admitted slugs.
    Returns 404 if the skill cannot be found.
    """
    result = await db.execute(
        _eager_skill().where(Skill.slug == slug, Skill.is_deleted.is_(False))
    )
    skill = result.scalar_one_or_none()

    if skill:
        sorted_versions = _sort_versions(list(skill.versions))
        latest = sorted_versions[0] if sorted_versions else None
        owner = skill.owner
        tags = skill.tags if isinstance(skill.tags, list) else parse_tags(skill.tags)
        return SkillDetailResponse(
            skill=SkillListItem(
                slug=skill.slug,
                displayName=skill.display_name,
                summary=skill.summary,
                tags=tags,
                stats=SkillStats(downloads=0),
                createdAt=skill.created_at,
                updatedAt=skill.updated_at,
            ),
            latestVersion=VersionInfo(
                version=latest.version,
                createdAt=latest.created_at,
                changelog=latest.changelog,
            )
            if latest
            else None,
            owner=OwnerInfo(
                handle=owner.username,
                displayName=owner.username,
            ),
        )

    # Try upstream proxy
    if await _check_admission(slug, None, db):
        proxy: UpstreamProxy = request.app.state.proxy
        upstream_data = await proxy.get_skill(slug)
        if upstream_data:
            return SkillDetailResponse(**upstream_data)

    raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")


# ---------------------------------------------------------------------------
# Skill versions
# ---------------------------------------------------------------------------

@router.get("/skills/{slug}/versions", response_model=SkillVersionsResponse)
async def get_skill_versions(
    slug: str,
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
) -> SkillVersionsResponse:
    """List all versions for a skill, ordered by created_at descending."""
    skill = await _get_skill_or_404(slug, db)
    sorted_versions = _sort_versions(list(skill.versions))
    return SkillVersionsResponse(
        versions=[
            VersionInfo(
                version=v.version,
                createdAt=v.created_at,
                changelog=v.changelog,
            )
            for v in sorted_versions
        ]
    )


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

@router.post("/skills", response_model=PublishResponse)
async def publish_skill(
    request: Request,
    slug: str = Form(..., description="Unique skill slug"),
    version: str = Form(..., description="Semantic version string"),
    display_name: Optional[str] = Form(None, description="Human-readable name"),
    summary: Optional[str] = Form(None, description="Short description"),
    changelog: Optional[str] = Form(None, description="Version changelog"),
    tags: Optional[str] = Form(
        None, description="Comma-separated tags"
    ),
    file: UploadFile = File(..., description="Skill zip archive"),
    user: User = Depends(require_role("admin", "publisher")),
    db: AsyncSession = Depends(get_session),
) -> PublishResponse:
    """Publish a new skill version (multipart upload).

    Creates the skill if it doesn't exist, or adds a new version if it does.
    Requires publisher or admin role.
    """
    storage: StorageBackend = request.app.state.storage

    # Validate slug format
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must be lowercase alphanumeric with hyphens only, "
            "matching pattern: ^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        )

    # Read the uploaded zip
    zip_data = await file.read()
    if not zip_data:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    storage_key = f"skills/{slug}/{version}.zip"

    # Get or create skill
    result = await db.execute(_eager_skill().where(Skill.slug == slug))
    skill = result.scalar_one_or_none()

    now = _now_ms()

    # Parse tags: accept comma-separated string and store as a list (JSON column)
    tag_list: list[str] = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if skill:
        # Check for duplicate version
        for v in skill.versions:
            if v.version == version:
                raise HTTPException(
                    status_code=409,
                    detail=f"Version {version} already exists for {slug}.",
                )
        if skill.is_deleted:
            skill.is_deleted = False
        skill.updated_at = now
        if display_name:
            skill.display_name = display_name
        if summary is not None:
            skill.summary = summary
        if tags is not None:
            skill.tags = tag_list
    else:
        skill = Skill(
            slug=slug,
            display_name=display_name or slug,
            summary=summary or "",
            tags=tag_list,
            owner_id=user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(skill)
        await db.flush()

    # Store the zip
    await storage.upload(storage_key, zip_data)

    # Create version record
    db.add(
        SkillVersion(
            skill_id=skill.id,
            version=version,
            changelog=changelog or "",
            storage_key=storage_key,
            file_size=len(zip_data),
            created_at=now,
        )
    )

    # Update FTS index (SQLite only; triggers may not fire with async ORM)
    try:
        await db.execute(
            text(
                "INSERT INTO skill_fts(rowid, slug, display_name, summary) "
                "VALUES(:id, :slug, :dn, :summary)"
            ),
            {
                "id": skill.id,
                "slug": skill.slug,
                "dn": skill.display_name,
                "summary": skill.summary or "",
            },
        )
    except Exception:
        logger.debug("FTS insert skipped (may not be SQLite)", exc_info=True)

    await db.commit()

    return PublishResponse(slug=slug, version=version)


# ---------------------------------------------------------------------------
# Delete (soft)
# ---------------------------------------------------------------------------

@router.delete("/skills/{slug}", status_code=200)
async def delete_skill(
    slug: str,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Soft-delete a skill (admin only).

    Sets is_deleted=True rather than removing the record.
    """
    skill = await _get_skill_or_404(slug, db)
    skill.is_deleted = True
    skill.updated_at = _now_ms()
    await db.commit()
    return {"message": "Skill deleted"}
