"""Well-known discovery endpoint for ClawHub CLI compatibility."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/.well-known/clawhub.json")
async def clawhub_discovery(request: Request) -> dict:
    base_url = str(request.base_url).rstrip("/")
    return {"apiBase": f"{base_url}/api/v1"}
