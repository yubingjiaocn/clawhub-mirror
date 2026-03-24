"""ClawHub Mirror - FastAPI application entry point.

Enterprise skill registry proxy that serves internal skills directly
and proxies approved external skills from upstream ClawHub.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clawhub_mirror.config import load_config
from clawhub_mirror.database import create_tables, init_db, get_db
from clawhub_mirror.models import create_fts_tables
from clawhub_mirror.proxy import UpstreamProxy
from clawhub_mirror.routers import admin, discovery, skills, whoami
from clawhub_mirror.storage import create_storage, StorageBackend
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    settings = load_config()
    app.state.settings = settings

    # Initialize database
    engine = init_db(settings)
    await create_tables()
    await create_fts_tables(engine)
    logger.info("Database initialized")

    # Initialize storage backend
    storage = create_storage(settings)
    app.state.storage = storage
    logger.info("Storage backend: %s", settings.storage_backend)

    # Initialize upstream proxy
    proxy = UpstreamProxy(settings, storage)
    app.state.proxy = proxy
    logger.info("Upstream proxy: %s", settings.upstream_url)

    yield

    # Shutdown
    await proxy.close()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ClawHub Mirror",
        description="Enterprise skill registry proxy for ClawHub",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS - load settings for middleware config
    settings = load_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(discovery.router)
    app.include_router(skills.router)
    app.include_router(admin.router)
    app.include_router(whoami.router)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict:
        """Health check — verifies DB and storage connectivity."""
        checks: dict[str, str] = {}

        # DB check
        try:
            async for db in get_db():
                await db.execute(text("SELECT 1"))
                checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {e}"

        # Storage check
        try:
            storage: StorageBackend = app.state.storage
            await storage.exists("__healthz__")
            checks["storage"] = "ok"
        except Exception as e:
            checks["storage"] = f"error: {e}"

        # Upstream reachability (non-blocking, best-effort)
        try:
            proxy: UpstreamProxy = app.state.proxy
            if proxy and proxy._client:
                resp = await proxy._client.head(
                    f"{app.state.settings.upstream_url}/.well-known/clawhub.json",
                    timeout=3.0,
                )
                checks["upstream"] = "ok" if resp.status_code < 500 else f"http {resp.status_code}"
            else:
                checks["upstream"] = "disabled"
        except Exception:
            checks["upstream"] = "unreachable"

        all_ok = all(v == "ok" for k, v in checks.items() if k != "upstream")
        status_code = 200 if all_ok else 503

        from starlette.responses import JSONResponse
        return JSONResponse(
            content={"status": "ok" if all_ok else "degraded", "checks": checks},
            status_code=status_code,
        )

    return app


app = create_app()
