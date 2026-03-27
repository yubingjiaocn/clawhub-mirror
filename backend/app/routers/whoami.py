"""Whoami endpoint returning current user info."""

from fastapi import APIRouter, Depends

from ..auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/whoami")
async def whoami(user: dict = Depends(get_current_user)) -> dict:
    # Return both ClawHub CLI format (nested user) and our extended fields
    return {
        "user": {
            "handle": user["username"],
            "displayName": user.get("username"),
            "image": None,
        },
        "username": user["username"],
        "role": user["role"],
        "handle": user["username"],
    }
