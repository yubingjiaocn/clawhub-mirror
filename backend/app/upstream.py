"""Upstream proxy: fetch skills from public ClawHub and cache locally."""

import logging

import httpx

from . import dynamodb, storage
from .schemas import normalize_tags

logger = logging.getLogger(__name__)

DEFAULT_UPSTREAM = "https://clawhub.ai"
TIMEOUT = 10.0

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
    return _client


def is_proxy_enabled() -> tuple[bool, str]:
    """Return (enabled, upstream_base_url)."""
    setting = dynamodb.get_setting("proxy")
    if not setting or not setting.get("enabled"):
        return False, DEFAULT_UPSTREAM
    return True, setting.get("upstreamUrl", DEFAULT_UPSTREAM)


async def resolve_upstream(slug: str, hash: str | None = None) -> dict | None:
    enabled, base = is_proxy_enabled()
    if not enabled:
        return None
    try:
        params: dict[str, str] = {"slug": slug}
        if hash:
            params["hash"] = hash
        r = await _get_client().get(f"{base}/api/v1/resolve", params=params)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.warning("Upstream resolve failed for %s: %s", slug, e)
    return None


async def download_upstream(slug: str, version: str) -> bytes | None:
    enabled, base = is_proxy_enabled()
    if not enabled:
        return None
    try:
        r = await _get_client().get(
            f"{base}/api/v1/download",
            params={"slug": slug, "version": version},
        )
        if r.status_code == 200:
            return r.content
    except Exception as e:
        logger.warning("Upstream download failed for %s@%s: %s", slug, version, e)
    return None


async def search_upstream(q: str, limit: int = 20) -> list[dict]:
    enabled, base = is_proxy_enabled()
    if not enabled:
        return []
    try:
        r = await _get_client().get(
            f"{base}/api/v1/search",
            params={"q": q, "limit": str(limit)},
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("results", [])
    except Exception as e:
        logger.warning("Upstream search failed for %r: %s", q, e)
    return []


async def fetch_skill_detail(slug: str) -> dict | None:
    enabled, base = is_proxy_enabled()
    if not enabled:
        return None
    try:
        r = await _get_client().get(f"{base}/api/v1/skills/{slug}")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.warning("Upstream skill detail failed for %s: %s", slug, e)
    return None


async def fetch_skill_versions(slug: str) -> list[dict]:
    enabled, base = is_proxy_enabled()
    if not enabled:
        return []
    try:
        r = await _get_client().get(f"{base}/api/v1/skills/{slug}/versions")
        if r.status_code == 200:
            data = r.json()
            return data.get("versions", [])
    except Exception as e:
        logger.warning("Upstream versions failed for %s: %s", slug, e)
    return []


def cache_skill_metadata(slug: str, detail: dict) -> None:
    """Cache upstream skill metadata into DynamoDB."""
    try:
        skill = detail.get("skill", detail)
        existing = dynamodb.get_skill(slug)
        if existing:
            return  # Already cached or local, don't overwrite

        dynamodb.put_skill(
            slug=slug,
            display_name=skill.get("displayName", slug),
            summary=skill.get("summary", ""),
            tags=normalize_tags(skill.get("tags", [])),
            owner_username="__upstream__",
        )
        # Mark as external
        dynamodb.update_skill(slug, isExternal=True)

        # Cache version info
        latest = detail.get("latestVersion") or skill.get("latestVersion")
        if latest and latest.get("version"):
            existing_ver = dynamodb.get_version(slug, latest["version"])
            if not existing_ver:
                dynamodb.put_version(
                    slug=slug,
                    version=latest["version"],
                    changelog=latest.get("changelog", ""),
                    storage_key=f"skills/{slug}/{latest['version']}.zip",
                    file_size=0,
                )
    except Exception as e:
        logger.warning("Failed to cache metadata for %s: %s", slug, e)


def cache_skill_archive(slug: str, version: str, data: bytes) -> None:
    """Cache upstream skill archive into S3 + DynamoDB."""
    try:
        storage_key = f"skills/{slug}/{version}.zip"
        storage.upload(storage_key, data)

        existing_ver = dynamodb.get_version(slug, version)
        if not existing_ver:
            dynamodb.put_version(
                slug=slug,
                version=version,
                changelog="",
                storage_key=storage_key,
                file_size=len(data),
            )
    except Exception as e:
        logger.warning("Failed to cache archive for %s@%s: %s", slug, version, e)
