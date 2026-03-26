"""ClawHub Enterprise - FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import admin, discovery, skills, whoami
from . import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClawHub Enterprise",
        description="Self-hosted ClawHub-compatible skill registry",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(discovery.router)
    app.include_router(skills.router)
    app.include_router(admin.router)
    app.include_router(whoami.router)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict:
        checks: dict[str, str] = {}

        try:
            from . import dynamodb as _ddb
            _ddb.get_table().table_status
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {e}"

        try:
            storage.exists("__healthz__")
            checks["storage"] = "ok"
        except Exception as e:
            checks["storage"] = f"error: {e}"

        all_ok = all(v == "ok" for v in checks.values())
        status_code = 200 if all_ok else 503

        from starlette.responses import JSONResponse
        return JSONResponse(
            content={"status": "ok" if all_ok else "degraded", "checks": checks},
            status_code=status_code,
        )

    return app


app = create_app()
