"""Shared test fixtures for clawhub-mirror tests."""

import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clawhub_mirror.auth import generate_api_token, hash_password
from clawhub_mirror.database import get_db, get_session
from clawhub_mirror.main import create_app
from clawhub_mirror.models import Base, User, create_fts_tables
from clawhub_mirror.storage import LocalStorage

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app():
    """Create a test application with in-memory database."""
    test_app = create_app()

    engine = create_async_engine(TEST_DB_URL, echo=False)
    test_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await create_fts_tables(engine)

    # Create temp storage
    tmp_dir = tempfile.mkdtemp()
    storage = LocalStorage(tmp_dir)

    # Override dependencies
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_session] = override_get_db
    test_app.state.storage = storage
    test_app.state.settings = type("Settings", (), {"upstream_url": "https://clawhub.ai"})()

    # Create a mock proxy that doesn't hit upstream
    from unittest.mock import AsyncMock
    mock_proxy = AsyncMock()
    mock_proxy.check_admission = AsyncMock(return_value=False)
    mock_proxy.resolve = AsyncMock(return_value=None)
    mock_proxy.download = AsyncMock(return_value=None)
    mock_proxy.search = AsyncMock(return_value=None)
    mock_proxy.get_skill = AsyncMock(return_value=None)
    mock_proxy.get_versions = AsyncMock(return_value=None)
    test_app.state.proxy = mock_proxy

    yield test_app, test_session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def admin_token(app) -> str:
    """Create an admin user and return their API token."""
    test_app, session_factory = app
    token = generate_api_token()
    async with session_factory() as session:
        import time
        user = User(
            username="testadmin",
            hashed_password=hash_password("adminpass"),
            role="admin",
            api_token=token,
            created_at=int(time.time() * 1000),
        )
        session.add(user)
        await session.commit()
    return token


@pytest_asyncio.fixture
async def publisher_token(app) -> str:
    """Create a publisher user and return their API token."""
    test_app, session_factory = app
    token = generate_api_token()
    async with session_factory() as session:
        import time
        user = User(
            username="testpublisher",
            hashed_password=hash_password("pubpass"),
            role="publisher",
            api_token=token,
            created_at=int(time.time() * 1000),
        )
        session.add(user)
        await session.commit()
    return token


@pytest_asyncio.fixture
async def reader_token(app) -> str:
    """Create a reader user and return their API token."""
    test_app, session_factory = app
    token = generate_api_token()
    async with session_factory() as session:
        import time
        user = User(
            username="testreader",
            hashed_password=hash_password("readpass"),
            role="reader",
            api_token=token,
            created_at=int(time.time() * 1000),
        )
        session.add(user)
        await session.commit()
    return token


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    test_app, _ = app
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
