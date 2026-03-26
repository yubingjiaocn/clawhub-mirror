"""Authentication: Bearer token auth using GSI3 token lookup."""

import secrets

import bcrypt
from fastapi import Depends, HTTPException, Request, status

from . import dynamodb


ADMIN = "admin"
PUBLISHER = "publisher"
READER = "reader"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_api_token() -> str:
    return secrets.token_urlsafe(32)


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token.",
        )
    return token


async def get_current_user(request: Request) -> dict:
    token = _extract_token(request)
    user = dynamodb.get_user_by_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API token.",
        )
    return user


def require_role(*roles: str):
    async def _check_role(request: Request) -> dict:
        user = await get_current_user(request)
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.get('role')}' is not authorized. "
                f"Required: {', '.join(roles)}.",
            )
        return user
    return _check_role


async def get_optional_user(request: Request) -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None
    return dynamodb.get_user_by_token(token)
