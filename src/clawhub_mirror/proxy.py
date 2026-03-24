"""Proxy logic for forwarding requests to upstream ClawHub registry."""

import httpx
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .models import AdmissionPolicy
from .storage import StorageBackend

logger = logging.getLogger(__name__)


class UpstreamProxy:
    """Handles proxying requests to the upstream ClawHub registry."""

    def __init__(self, settings: Settings, storage: StorageBackend) -> None:
        self.upstream_url = settings.upstream_url.rstrip("/")
        self.storage = storage
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.upstream_url,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def check_admission(self, slug: str, version: str | None, db: AsyncSession) -> bool:
        """Check if a slug (and optionally version) is allowed by admission policy.

        Returns True if allowed, False if denied or no policy exists.
        """
        stmt = select(AdmissionPolicy).where(
            AdmissionPolicy.slug == slug,
            AdmissionPolicy.policy_type == "allow",
        )
        result = await db.execute(stmt)
        policy = result.scalar_one_or_none()

        if policy is None:
            return False

        # If allowed_versions is set, check version is in the list
        if policy.allowed_versions and version:
            allowed = [v.strip() for v in policy.allowed_versions.split(",")]
            return version in allowed

        # No version restriction or no version specified
        return True

    async def resolve(self, slug: str, hash_val: str | None = None) -> dict | None:
        """Proxy a resolve request to upstream."""
        client = await self._get_client()
        params: dict[str, str] = {"slug": slug}
        if hash_val:
            params["hash"] = hash_val
        try:
            resp = await client.get("/api/v1/resolve", params=params)
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Upstream resolve failed for %s: %s", slug, e)
        return None

    async def download(self, slug: str, version: str) -> bytes | None:
        """Download a skill zip from upstream, caching it locally."""
        cache_key = f"cache/{slug}/{version}.zip"

        # Check cache first
        if await self.storage.exists(cache_key):
            logger.info("Cache hit for %s@%s", slug, version)
            return await self.storage.download(cache_key)

        # Fetch from upstream
        client = await self._get_client()
        try:
            resp = await client.get(
                "/api/v1/download",
                params={"slug": slug, "version": version},
            )
            if resp.status_code == 200:
                data = resp.content
                # Cache for future requests
                await self.storage.upload(cache_key, data)
                logger.info("Cached %s@%s (%d bytes)", slug, version, len(data))
                return data
        except httpx.HTTPError as e:
            logger.error("Upstream download failed for %s@%s: %s", slug, version, e)
        return None

    async def search(self, query: str, limit: int = 20) -> dict | None:
        """Proxy a search request to upstream."""
        client = await self._get_client()
        try:
            resp = await client.get(
                "/api/v1/search",
                params={"q": query, "limit": limit},
            )
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Upstream search failed: %s", e)
        return None

    async def get_skill(self, slug: str) -> dict | None:
        """Proxy a skill detail request to upstream."""
        client = await self._get_client()
        try:
            resp = await client.get(f"/api/v1/skills/{slug}")
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Upstream skill detail failed for %s: %s", slug, e)
        return None

    async def get_versions(self, slug: str) -> dict | None:
        """Proxy a versions list request to upstream."""
        client = await self._get_client()
        try:
            resp = await client.get(f"/api/v1/skills/{slug}/versions")
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Upstream versions failed for %s: %s", slug, e)
        return None
