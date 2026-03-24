"""Admin endpoints -- user management and admission policy CRUD."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from clawhub_mirror.auth import generate_api_token, hash_password, require_role
from clawhub_mirror.database import get_db
from clawhub_mirror.models import AdmissionPolicy, PendingRequest, User
from clawhub_mirror.schemas import (
    AdmissionPolicyCreateRequest,
    AdmissionPolicyListResponse,
    AdmissionPolicySchema,
    AdmissionPolicyUpdateRequest,
    PendingRequestListResponse,
    PendingRequestSchema,
    UserCreateRequest,
    UserCreateResponse,
    UserSchema,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_admin_dep = require_role("admin")


def _now_ms() -> int:
    """Current time as Unix epoch milliseconds."""
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.post("/users", response_model=UserCreateResponse)
async def create_user(
    body: UserCreateRequest,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> UserCreateResponse:
    """Create a new user (admin only).

    Hashes the provided password and generates an API token.
    """
    existing = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Username already exists: {body.username}",
        )

    if body.role not in ("admin", "publisher", "reader"):
        raise HTTPException(
            status_code=400,
            detail="Role must be admin, publisher, or reader.",
        )

    token = generate_api_token()
    new_user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        api_token=token,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return UserCreateResponse(
        user=UserSchema(
            id=new_user.id,
            username=new_user.username,
            role=new_user.role,
            isActive=new_user.is_active,
            createdAt=new_user.created_at,
        ),
        apiToken=token,
    )


@router.get("/users", response_model=list[UserSchema])
async def list_users(
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> list[UserSchema]:
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [
        UserSchema(
            id=u.id,
            username=u.username,
            role=u.role,
            isActive=u.is_active,
            createdAt=u.created_at,
        )
        for u in users
    ]


@router.delete("/users/{username}", status_code=200)
async def deactivate_user(
    username: str,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a user by setting is_active=False (admin only)."""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404, detail=f"User not found: {username}"
        )
    target.is_active = False
    return {"detail": f"User {username} has been deactivated."}


# ---------------------------------------------------------------------------
# Admission policies
# ---------------------------------------------------------------------------

@router.get("/policies", response_model=AdmissionPolicyListResponse)
async def list_policies(
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> AdmissionPolicyListResponse:
    """List all admission policies."""
    result = await db.execute(
        select(AdmissionPolicy).order_by(AdmissionPolicy.id)
    )
    policies = result.scalars().all()
    return AdmissionPolicyListResponse(
        policies=[
            AdmissionPolicySchema(
                id=p.id,
                slug=p.slug,
                allowedVersions=p.allowed_versions,
                policyType=p.policy_type,
                approvedBy=p.approved_by,
                approvedAt=p.approved_at,
                notes=p.notes,
                createdAt=p.created_at,
            )
            for p in policies
        ]
    )


@router.post("/policies", response_model=AdmissionPolicySchema)
async def create_policy(
    body: AdmissionPolicyCreateRequest,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> AdmissionPolicySchema:
    """Create an admission policy for an external skill slug.

    Sets approved_by to the current user's username.
    """
    policy_type = body.policy_type or "allow"
    if policy_type not in ("allow", "deny"):
        raise HTTPException(
            status_code=400,
            detail="policy_type must be 'allow' or 'deny'.",
        )

    existing = await db.execute(
        select(AdmissionPolicy).where(AdmissionPolicy.slug == body.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Policy already exists for slug '{body.slug}'.",
        )

    now = _now_ms()
    policy = AdmissionPolicy(
        slug=body.slug,
        allowed_versions=body.allowed_versions,
        policy_type=policy_type,
        approved_by=user.username,
        approved_at=now,
        notes=body.notes,
    )
    db.add(policy)

    await db.execute(
        delete(PendingRequest).where(PendingRequest.slug == body.slug)
    )

    await db.flush()
    await db.refresh(policy)

    return AdmissionPolicySchema(
        id=policy.id,
        slug=policy.slug,
        allowedVersions=policy.allowed_versions,
        policyType=policy.policy_type,
        approvedBy=policy.approved_by,
        approvedAt=policy.approved_at,
        notes=policy.notes,
        createdAt=policy.created_at,
    )


@router.put("/policies/{slug}", response_model=AdmissionPolicySchema)
async def update_policy(
    slug: str,
    body: AdmissionPolicyUpdateRequest,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> AdmissionPolicySchema:
    """Update an existing admission policy by slug."""
    result = await db.execute(
        select(AdmissionPolicy).where(AdmissionPolicy.slug == slug)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    if body.policy_type is not None:
        if body.policy_type not in ("allow", "deny"):
            raise HTTPException(
                status_code=400,
                detail="policy_type must be 'allow' or 'deny'.",
            )
        policy.policy_type = body.policy_type

    if body.allowed_versions is not None:
        policy.allowed_versions = body.allowed_versions
    if body.notes is not None:
        policy.notes = body.notes

    policy.approved_by = user.username
    policy.approved_at = _now_ms()

    return AdmissionPolicySchema(
        id=policy.id,
        slug=policy.slug,
        allowedVersions=policy.allowed_versions,
        policyType=policy.policy_type,
        approvedBy=policy.approved_by,
        approvedAt=policy.approved_at,
        notes=policy.notes,
        createdAt=policy.created_at,
    )


@router.delete("/policies/{slug}", status_code=200)
async def delete_policy(
    slug: str,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an admission policy by slug."""
    result = await db.execute(
        select(AdmissionPolicy).where(AdmissionPolicy.slug == slug)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    await db.delete(policy)
    return {"detail": f"Policy for '{slug}' deleted."}


# ---------------------------------------------------------------------------
# Pending requests
# ---------------------------------------------------------------------------

@router.get("/policies/pending", response_model=PendingRequestListResponse)
async def list_pending(
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> PendingRequestListResponse:
    """List skills that were requested but not yet approved."""
    result = await db.execute(
        select(PendingRequest)
        .where(PendingRequest.status == "pending")
        .order_by(PendingRequest.requested_at.desc())
    )
    requests = result.scalars().all()
    return PendingRequestListResponse(
        requests=[
            PendingRequestSchema(
                id=r.id,
                slug=r.slug,
                requestedBy=r.requested_by,
                requestedAt=r.requested_at,
                reason=r.reason,
                status=r.status,
            )
            for r in requests
        ]
    )


@router.post("/policies/pending/{request_id}/approve", status_code=200)
async def approve_pending(
    request_id: int,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> AdmissionPolicySchema:
    """Approve a pending request by creating an allow policy.

    Creates an AdmissionPolicy with policy_type='allow' for the requested slug
    and updates the pending request status to 'approved'.
    """
    result = await db.execute(
        select(PendingRequest).where(PendingRequest.id == request_id)
    )
    pending = result.scalar_one_or_none()
    if not pending:
        raise HTTPException(
            status_code=404, detail="Pending request not found."
        )

    existing = await db.execute(
        select(AdmissionPolicy).where(AdmissionPolicy.slug == pending.slug)
    )
    if existing.scalar_one_or_none():
        pending.status = "approved"
        raise HTTPException(
            status_code=409,
            detail=f"Policy already exists for '{pending.slug}'.",
        )

    now = _now_ms()
    policy = AdmissionPolicy(
        slug=pending.slug,
        policy_type="allow",
        approved_by=user.username,
        approved_at=now,
        notes=f"Approved from pending request #{request_id}",
    )
    db.add(policy)
    pending.status = "approved"
    await db.flush()
    await db.refresh(policy)

    return AdmissionPolicySchema(
        id=policy.id,
        slug=policy.slug,
        allowedVersions=policy.allowed_versions,
        policyType=policy.policy_type,
        approvedBy=policy.approved_by,
        approvedAt=policy.approved_at,
        notes=policy.notes,
        createdAt=policy.created_at,
    )


@router.post("/policies/pending/{request_id}/deny", status_code=200)
async def deny_pending(
    request_id: int,
    user: User = Depends(_admin_dep),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deny a pending request by updating its status to 'denied'."""
    result = await db.execute(
        select(PendingRequest).where(PendingRequest.id == request_id)
    )
    pending = result.scalar_one_or_none()
    if not pending:
        raise HTTPException(
            status_code=404, detail="Pending request not found."
        )

    slug = pending.slug
    pending.status = "denied"

    return {"detail": f"Pending request for '{slug}' has been denied."}
