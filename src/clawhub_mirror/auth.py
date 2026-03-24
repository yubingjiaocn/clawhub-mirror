"""Authentication and authorization utilities for ClawHub Mirror.

Provides password hashing, API token generation, and FastAPI dependencies
for extracting and verifying the current user from incoming requests.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clawhub_mirror.database import get_db
from clawhub_mirror.models import User

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------
ADMIN: str = "admin"
PUBLISHER: str = "publisher"
READER: str = "reader"


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        password: The plaintext password to check.
        hashed: The stored bcrypt hash.

    Returns:
        True if the password matches the hash.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Token generation
# ---------------------------------------------------------------------------
def generate_api_token() -> str:
    """Generate a cryptographically secure API token.

    Returns:
        A URL-safe random token string (43 characters).
    """
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency that extracts and validates the current user.

    Expects an ``Authorization: Bearer <token>`` header. Looks up the user
    by their ``api_token`` field and verifies the account is active.

    Args:
        request: The incoming FastAPI request.
        db: Async database session (injected).

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException: 401 if the token is missing, invalid, or the user is inactive.
    """
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

    result = await db.execute(select(User).where(User.api_token == token))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API token.",
        )

    return user


def require_role(*roles: str) -> Callable:
    """Create a FastAPI dependency that enforces role-based access.

    Args:
        *roles: One or more role strings that are permitted access.

    Returns:
        A FastAPI dependency function.

    Example::

        @router.post("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(ADMIN))):
            ...
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized. "
                f"Required: {', '.join(roles)}.",
            )
        return current_user

    return _check_role


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> "User | None":
    """Like get_current_user but returns None instead of raising 401."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None
    from sqlalchemy import select as _select
    result = await db.execute(_select(User).where(User.api_token == token))
    user = result.scalar_one_or_none()
    return user if (user and user.is_active) else None
