"""Whoami endpoint returning current user info."""

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..schemas import WhoamiResponse

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(user: dict = Depends(get_current_user)) -> WhoamiResponse:
    return WhoamiResponse(
        username=user["username"],
        role=user["role"],
        handle=user["username"],
    )
