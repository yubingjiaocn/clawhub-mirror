"""Admin endpoints: user management and admission policy CRUD."""

from fastapi import APIRouter, Depends, HTTPException

from ..auth import generate_api_token, hash_password, require_role
from .. import dynamodb
from ..schemas import (
    AdmissionPolicyCreateRequest,
    AdmissionPolicyListResponse,
    AdmissionPolicySchema,
    AdmissionPolicyUpdateRequest,
    PendingRequestListResponse,
    PendingRequestSchema,
    ProxySettingsRequest,
    UserCreateRequest,
    UserCreateResponse,
    UserSchema,
    UserUpdateRoleRequest,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_admin_dep = require_role("admin")


def _make_policy_schema(p: dict) -> AdmissionPolicySchema:
    return AdmissionPolicySchema(
        id=p.get("slug", ""),
        slug=p["slug"],
        allowedVersions=p.get("allowedVersions"),
        policyType=p["policyType"],
        approvedBy=p.get("approvedBy"),
        approvedAt=p.get("approvedAt"),
        notes=p.get("notes"),
        createdAt=p.get("createdAt", 0),
    )


def _pending_id(item: dict) -> str:
    """Composite ID from PK/SK: slug::timestamp."""
    pk = item.get("PK", "")
    sk = item.get("SK", "")
    slug = pk.removeprefix("PENDING#")
    ts = sk.removeprefix("REQ#")
    return f"{slug}::{ts}"


# --- User management ---

@router.post("/users", response_model=UserCreateResponse)
async def create_user(
    body: UserCreateRequest,
    user: dict = Depends(_admin_dep),
) -> UserCreateResponse:
    existing = dynamodb.get_user(body.username)
    if existing:
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
    new_user = dynamodb.put_user(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        api_token=token,
    )

    return UserCreateResponse(
        user=UserSchema(
            username=new_user["username"],
            role=new_user["role"],
            isActive=new_user["isActive"],
            createdAt=new_user["createdAt"],
        ),
        apiToken=token,
    )


@router.get("/users", response_model=list[UserSchema])
async def list_users(
    user: dict = Depends(_admin_dep),
) -> list[UserSchema]:
    users = dynamodb.list_users()
    return [
        UserSchema(
            username=u["username"],
            role=u["role"],
            isActive=u.get("isActive", True),
            createdAt=u.get("createdAt", 0),
        )
        for u in users
    ]


@router.patch("/users/{username}", response_model=UserSchema)
async def update_user_role(
    username: str,
    body: UserUpdateRoleRequest,
    user: dict = Depends(_admin_dep),
) -> UserSchema:
    target = dynamodb.get_user(username)
    if not target:
        raise HTTPException(status_code=404, detail=f"User not found: {username}")

    if body.role not in ("admin", "publisher", "reader"):
        raise HTTPException(
            status_code=400,
            detail="Role must be admin, publisher, or reader.",
        )

    updated = dynamodb.update_user_role(username, body.role)
    return UserSchema(
        username=updated["username"],
        role=updated["role"],
        isActive=updated.get("isActive", True),
        createdAt=updated.get("createdAt", 0),
    )


@router.delete("/users/{username}", status_code=200)
async def deactivate_user(
    username: str,
    user: dict = Depends(_admin_dep),
) -> dict:
    target = dynamodb.get_user(username)
    if not target:
        raise HTTPException(status_code=404, detail=f"User not found: {username}")
    dynamodb.deactivate_user(username)
    return {"detail": f"User {username} has been deactivated."}


# --- Admission policies ---

@router.get("/policies", response_model=AdmissionPolicyListResponse)
async def list_policies(
    user: dict = Depends(_admin_dep),
) -> AdmissionPolicyListResponse:
    policies = dynamodb.list_policies()
    return AdmissionPolicyListResponse(
        policies=[_make_policy_schema(p) for p in policies]
    )


@router.post("/policies", response_model=AdmissionPolicySchema)
async def create_policy(
    body: AdmissionPolicyCreateRequest,
    user: dict = Depends(_admin_dep),
) -> AdmissionPolicySchema:
    policy_type = body.policy_type or "allow"
    if policy_type not in ("allow", "deny"):
        raise HTTPException(
            status_code=400,
            detail="policy_type must be 'allow' or 'deny'.",
        )

    existing = dynamodb.get_policy(body.slug)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Policy already exists for slug '{body.slug}'.",
        )

    policy = dynamodb.put_policy(
        slug=body.slug,
        policy_type=policy_type,
        approved_by=user["username"],
        allowed_versions=body.allowed_versions,
        notes=body.notes,
    )

    dynamodb.delete_pending_for_slug(body.slug)

    return _make_policy_schema(policy)


@router.patch("/policies/{slug}", response_model=AdmissionPolicySchema)
async def update_policy(
    slug: str,
    body: AdmissionPolicyUpdateRequest,
    user: dict = Depends(_admin_dep),
) -> AdmissionPolicySchema:
    existing = dynamodb.get_policy(slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found.")

    updates = {}
    if body.policy_type is not None:
        if body.policy_type not in ("allow", "deny"):
            raise HTTPException(
                status_code=400,
                detail="policy_type must be 'allow' or 'deny'.",
            )
        updates["policyType"] = body.policy_type
    if body.allowed_versions is not None:
        updates["allowedVersions"] = body.allowed_versions
    if body.notes is not None:
        updates["notes"] = body.notes

    policy = dynamodb.update_policy(slug, approved_by=user["username"], **updates)

    return _make_policy_schema(policy)


@router.delete("/policies/{slug}", status_code=200)
async def delete_policy(
    slug: str,
    user: dict = Depends(_admin_dep),
) -> dict:
    existing = dynamodb.get_policy(slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found.")
    dynamodb.delete_policy(slug)
    return {"detail": f"Policy for '{slug}' deleted."}


# --- Pending requests ---

@router.get("/policies/pending", response_model=PendingRequestListResponse)
async def list_pending(
    user: dict = Depends(_admin_dep),
) -> PendingRequestListResponse:
    requests = dynamodb.list_pending_requests()
    return PendingRequestListResponse(
        requests=[
            PendingRequestSchema(
                id=_pending_id(r),
                slug=r["slug"],
                requestedBy=r.get("requestedBy"),
                requestedAt=r.get("requestedAt"),
                reason=r.get("reason"),
                status=r["status"],
            )
            for r in requests
        ]
    )


@router.post("/policies/pending/{request_id}/approve", status_code=200)
async def approve_pending(
    request_id: str,
    user: dict = Depends(_admin_dep),
) -> AdmissionPolicySchema:
    pending = dynamodb.get_pending_request(request_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending request not found.")

    slug = pending["slug"]
    existing = dynamodb.get_policy(slug)
    if existing:
        dynamodb.update_pending_status(request_id, "approved")
        raise HTTPException(
            status_code=409,
            detail=f"Policy already exists for '{slug}'.",
        )

    policy = dynamodb.put_policy(
        slug=slug,
        policy_type="allow",
        approved_by=user["username"],
        notes=f"Approved from pending request {request_id}",
    )
    dynamodb.update_pending_status(request_id, "approved")

    return _make_policy_schema(policy)


@router.post("/policies/pending/{request_id}/deny", status_code=200)
async def deny_pending(
    request_id: str,
    user: dict = Depends(_admin_dep),
) -> dict:
    pending = dynamodb.get_pending_request(request_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending request not found.")

    slug = pending["slug"]
    dynamodb.update_pending_status(request_id, "denied")
    return {"detail": f"Pending request for '{slug}' has been denied."}


# --- Proxy settings ---

@router.get("/settings/proxy")
async def get_proxy_settings(
    user: dict = Depends(_admin_dep),
) -> dict:
    setting = dynamodb.get_setting("proxy")
    return {
        "enabled": setting.get("enabled", False) if setting else False,
        "upstreamUrl": setting.get("upstreamUrl", "https://clawhub.ai") if setting else "https://clawhub.ai",
    }


@router.put("/settings/proxy")
async def update_proxy_settings(
    body: ProxySettingsRequest,
    user: dict = Depends(_admin_dep),
) -> dict:
    dynamodb.put_setting(
        "proxy",
        enabled=body.enabled,
        upstreamUrl=body.upstream_url or "https://clawhub.ai",
    )
    return {
        "enabled": body.enabled,
        "upstreamUrl": body.upstream_url or "https://clawhub.ai",
    }
