"""DynamoDB client and CRUD operations using single-table design."""

import time
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from .config import settings

_table = None


def _now_ms() -> int:
    return int(time.time() * 1000)


def get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name=settings.REGION)
        _table = dynamodb.Table(settings.TABLE_NAME)
    return _table


# --- Skill CRUD ---

def put_skill(slug: str, display_name: str, summary: str, tags: list[str],
              owner_username: str, readme: str = "") -> dict:
    now = _now_ms()
    item = {
        "PK": f"SKILL#{slug}",
        "SK": "META",
        "slug": slug,
        "displayName": display_name,
        "summary": summary,
        "tags": tags,
        "ownerUsername": owner_username,
        "readme": readme,
        "isDeleted": False,
        "isExternal": False,
        "createdAt": now,
        "updatedAt": now,
        "GSI1PK": "ALL_SKILLS",
        "GSI1SK": f"{now}#{slug}",
        "GSI2PK": f"OWNER#{owner_username}",
        "GSI2SK": f"{now}#{slug}",
    }
    get_table().put_item(Item=item)
    return item


def get_skill(slug: str) -> dict | None:
    resp = get_table().get_item(Key={"PK": f"SKILL#{slug}", "SK": "META"})
    item = resp.get("Item")
    if item and item.get("isDeleted"):
        return None
    return item


def update_skill(slug: str, **updates) -> dict | None:
    now = _now_ms()
    updates["updatedAt"] = now
    updates["GSI1SK"] = f"{now}#{slug}"

    expr_parts = []
    names = {}
    values = {}
    for i, (k, v) in enumerate(updates.items()):
        alias = f"#f{i}"
        val_alias = f":v{i}"
        expr_parts.append(f"{alias} = {val_alias}")
        names[alias] = k
        values[val_alias] = v

    # Also update GSI2SK if ownerUsername is available
    resp = get_table().update_item(
        Key={"PK": f"SKILL#{slug}", "SK": "META"},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes")


def soft_delete_skill(slug: str) -> bool:
    update_skill(slug, isDeleted=True)
    return True


def list_skills(limit: int = 50, cursor: str | None = None) -> tuple[list[dict], str | None]:
    kwargs: dict[str, Any] = {
        "IndexName": "GSI1",
        "KeyConditionExpression": Key("GSI1PK").eq("ALL_SKILLS"),
        "ScanIndexForward": False,
        "Limit": limit + 1,
        "FilterExpression": Attr("isDeleted").eq(False) | Attr("isDeleted").not_exists(),
    }
    if cursor:
        kwargs["ExclusiveStartKey"] = _decode_cursor(cursor)

    resp = get_table().query(**kwargs)
    items = resp.get("Items", [])

    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        next_cursor = _encode_cursor(resp.get("LastEvaluatedKey") or _make_gsi1_key(items[-1]))

    return items, next_cursor


def list_skills_by_owner(username: str, limit: int = 50) -> list[dict]:
    resp = get_table().query(
        IndexName="GSI2",
        KeyConditionExpression=Key("GSI2PK").eq(f"OWNER#{username}"),
        ScanIndexForward=False,
        Limit=limit,
        FilterExpression=Attr("isDeleted").eq(False) | Attr("isDeleted").not_exists(),
    )
    return resp.get("Items", [])


# --- Skill Versions ---

def put_version(slug: str, version: str, changelog: str, storage_key: str,
                file_size: int) -> dict:
    now = _now_ms()
    item = {
        "PK": f"SKILL#{slug}",
        "SK": f"VER#{version}",
        "version": version,
        "changelog": changelog,
        "storageKey": storage_key,
        "fileSize": file_size,
        "createdAt": now,
    }
    get_table().put_item(Item=item)
    return item


def get_version(slug: str, version: str) -> dict | None:
    resp = get_table().get_item(
        Key={"PK": f"SKILL#{slug}", "SK": f"VER#{version}"}
    )
    return resp.get("Item")


def list_versions(slug: str) -> list[dict]:
    resp = get_table().query(
        KeyConditionExpression=Key("PK").eq(f"SKILL#{slug}") & Key("SK").begins_with("VER#"),
        ScanIndexForward=False,
    )
    return resp.get("Items", [])


# --- User CRUD ---

def put_user(username: str, hashed_password: str, role: str, api_token: str) -> dict:
    now = _now_ms()
    item = {
        "PK": f"USER#{username}",
        "SK": "PROFILE",
        "username": username,
        "hashedPassword": hashed_password,
        "role": role,
        "apiToken": api_token,
        "isActive": True,
        "createdAt": now,
        "GSI3PK": f"TOKEN#{api_token}",
        "GSI3SK": "TOKEN",
    }
    get_table().put_item(Item=item)
    return item


def get_user(username: str) -> dict | None:
    resp = get_table().get_item(
        Key={"PK": f"USER#{username}", "SK": "PROFILE"}
    )
    return resp.get("Item")


def get_user_by_token(token: str) -> dict | None:
    resp = get_table().query(
        IndexName="GSI3",
        KeyConditionExpression=Key("GSI3PK").eq(f"TOKEN#{token}") & Key("GSI3SK").eq("TOKEN"),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return None
    item = items[0]
    # If this is an API key item, resolve to the actual user
    if item.get("SK", "").startswith("APIKEY#"):
        if item.get("isRevoked", False):
            return None
        user = get_user(item["username"])
        if user and user.get("isActive", True):
            return user
        return None
    # Direct user profile token
    if not item.get("isActive", True):
        return None
    return item


def list_users() -> list[dict]:
    resp = get_table().scan(
        FilterExpression=Key("SK").eq("PROFILE") & Key("PK").begins_with("USER#"),
    )
    return resp.get("Items", [])


def deactivate_user(username: str) -> bool:
    get_table().update_item(
        Key={"PK": f"USER#{username}", "SK": "PROFILE"},
        UpdateExpression="SET isActive = :v",
        ExpressionAttributeValues={":v": False},
    )
    return True


# --- API Keys ---

def put_api_key(username: str, token: str, label: str = "") -> dict:
    now = _now_ms()
    # Use first 8 chars as key_id for display/revocation
    key_id = token[:8]
    item = {
        "PK": f"USER#{username}",
        "SK": f"APIKEY#{key_id}",
        "username": username,
        "keyId": key_id,
        "label": label,
        "tokenPrefix": token[:12],
        "createdAt": now,
        "isRevoked": False,
        "GSI3PK": f"TOKEN#{token}",
        "GSI3SK": "TOKEN",
    }
    get_table().put_item(Item=item)
    return item


def list_api_keys(username: str) -> list[dict]:
    resp = get_table().query(
        KeyConditionExpression=Key("PK").eq(f"USER#{username}") & Key("SK").begins_with("APIKEY#"),
        ScanIndexForward=False,
    )
    return [k for k in resp.get("Items", []) if not k.get("isRevoked", False)]


def revoke_api_key(username: str, key_id: str) -> bool:
    try:
        get_table().update_item(
            Key={"PK": f"USER#{username}", "SK": f"APIKEY#{key_id}"},
            UpdateExpression="SET isRevoked = :v, GSI3PK = :empty, GSI3SK = :empty",
            ExpressionAttributeValues={":v": True, ":empty": "REVOKED"},
            ConditionExpression=Attr("PK").exists(),
        )
        return True
    except Exception:
        return False


# --- Sessions ---

def put_session(username: str, session_token: str, ttl_seconds: int = 86400) -> dict:
    now = _now_ms()
    expires_at = int(time.time()) + ttl_seconds
    item = {
        "PK": f"SESSION#{session_token}",
        "SK": "META",
        "username": username,
        "createdAt": now,
        "expiresAt": expires_at,
    }
    get_table().put_item(Item=item)
    return item


def get_session(session_token: str) -> dict | None:
    resp = get_table().get_item(
        Key={"PK": f"SESSION#{session_token}", "SK": "META"}
    )
    item = resp.get("Item")
    if not item:
        return None
    if item.get("expiresAt", 0) < int(time.time()):
        delete_session(session_token)
        return None
    return item


def delete_session(session_token: str) -> bool:
    get_table().delete_item(Key={"PK": f"SESSION#{session_token}", "SK": "META"})
    return True


# --- Admission Policies ---

def put_policy(slug: str, policy_type: str, approved_by: str,
               allowed_versions: str | None = None, notes: str | None = None) -> dict:
    now = _now_ms()
    item = {
        "PK": f"POLICY#{slug}",
        "SK": "META",
        "slug": slug,
        "allowedVersions": allowed_versions,
        "policyType": policy_type,
        "approvedBy": approved_by,
        "approvedAt": now,
        "notes": notes,
        "createdAt": now,
    }
    # Remove None values
    item = {k: v for k, v in item.items() if v is not None}
    get_table().put_item(Item=item)
    return item


def get_policy(slug: str) -> dict | None:
    resp = get_table().get_item(
        Key={"PK": f"POLICY#{slug}", "SK": "META"}
    )
    return resp.get("Item")


def update_policy(slug: str, approved_by: str, **updates) -> dict | None:
    now = _now_ms()
    updates["approvedBy"] = approved_by
    updates["approvedAt"] = now

    # Remove None values
    updates = {k: v for k, v in updates.items() if v is not None}

    expr_parts = []
    names = {}
    values = {}
    for i, (k, v) in enumerate(updates.items()):
        alias = f"#f{i}"
        val_alias = f":v{i}"
        expr_parts.append(f"{alias} = {val_alias}")
        names[alias] = k
        values[val_alias] = v

    resp = get_table().update_item(
        Key={"PK": f"POLICY#{slug}", "SK": "META"},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes")


def delete_policy(slug: str) -> bool:
    get_table().delete_item(Key={"PK": f"POLICY#{slug}", "SK": "META"})
    return True


def list_policies() -> list[dict]:
    resp = get_table().scan(
        FilterExpression=Attr("PK").begins_with("POLICY#") & Attr("SK").eq("META"),
    )
    return resp.get("Items", [])


# --- Pending Requests ---

def put_pending_request(slug: str, requested_by: str, reason: str | None = None) -> dict:
    now = _now_ms()
    item = {
        "PK": f"PENDING#{slug}",
        "SK": f"REQ#{now}",
        "slug": slug,
        "requestedBy": requested_by,
        "requestedAt": now,
        "reason": reason,
        "status": "pending",
    }
    item = {k: v for k, v in item.items() if v is not None}
    get_table().put_item(Item=item)
    return item


def list_pending_requests() -> list[dict]:
    resp = get_table().scan(
        FilterExpression=Attr("PK").begins_with("PENDING#") & Attr("status").eq("pending"),
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("requestedAt", 0), reverse=True)
    return items


def get_pending_request(request_id: str) -> dict | None:
    """Look up a pending request by its composite ID (slug::timestamp)."""
    parts = request_id.split("::", 1)
    if len(parts) != 2:
        return None
    slug, ts = parts
    resp = get_table().get_item(
        Key={"PK": f"PENDING#{slug}", "SK": f"REQ#{ts}"}
    )
    return resp.get("Item")


def update_pending_status(request_id: str, status: str) -> bool:
    parts = request_id.split("::", 1)
    if len(parts) != 2:
        return False
    slug, ts = parts
    get_table().update_item(
        Key={"PK": f"PENDING#{slug}", "SK": f"REQ#{ts}"},
        UpdateExpression="SET #s = :v",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":v": status},
    )
    return True


def delete_pending_for_slug(slug: str) -> None:
    """Delete all pending requests for a given slug."""
    resp = get_table().query(
        KeyConditionExpression=Key("PK").eq(f"PENDING#{slug}") & Key("SK").begins_with("REQ#"),
    )
    for item in resp.get("Items", []):
        get_table().delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


# --- Search (V1: DDB Scan with contains filter) ---

def search_skills(query: str, limit: int = 20) -> list[dict]:
    if not query.strip():
        items, _ = list_skills(limit=limit)
        return items

    q_lower = query.lower()
    resp = get_table().scan(
        FilterExpression=(
            Attr("SK").eq("META")
            & Attr("PK").begins_with("SKILL#")
            & (Attr("isDeleted").eq(False) | Attr("isDeleted").not_exists())
            & (
                Attr("slug").contains(q_lower)
                | Attr("displayName").contains(query)
                | Attr("summary").contains(query)
            )
        ),
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("updatedAt", 0), reverse=True)
    return items[:limit]


# --- Cursor helpers ---

import base64
import json as _json


def _encode_cursor(last_key: dict) -> str:
    return base64.urlsafe_b64encode(_json.dumps(last_key).encode()).decode()


def _decode_cursor(cursor: str) -> dict:
    return _json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


def _make_gsi1_key(item: dict) -> dict:
    return {
        "PK": item["PK"],
        "SK": item["SK"],
        "GSI1PK": item.get("GSI1PK", "ALL_SKILLS"),
        "GSI1SK": item.get("GSI1SK", ""),
    }
