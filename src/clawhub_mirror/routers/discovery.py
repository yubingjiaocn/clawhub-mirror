"""Well-known discovery endpoint for ClawHub CLI compatibility."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/.well-known/clawhub.json")
async def clawhub_discovery(request: Request) -> dict:
    """Return the API base URL for ClawHub CLI auto-discovery.

    The CLI checks OPENCLAW_CLAWHUB_URL or CLAWHUB_URL env vars,
    then fetches this endpoint to find the API base.
    """
    base_url = str(request.base_url).rstrip("/")
    return {"apiBase": f"{base_url}/api/v1"}
