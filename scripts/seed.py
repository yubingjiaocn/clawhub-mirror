#!/usr/bin/env python3
"""Seed script to create initial admin user and sample data.

Usage:
    uv run python scripts/seed.py

Creates:
    - An admin user with username 'admin' and a generated API token
    - A sample admission policy for demonstration
"""

import asyncio
import sys
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Adjust path for running from project root
sys.path.insert(0, "src")

from clawhub_mirror.auth import generate_api_token, hash_password
from clawhub_mirror.config import load_config
from clawhub_mirror.models import AdmissionPolicy, Base, User, create_fts_tables


async def seed() -> None:
    """Create initial database records."""
    settings = load_config()
    engine = create_async_engine(settings.database_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await create_fts_tables(engine)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        if result.scalar_one_or_none():
            print("Admin user already exists, skipping user creation.")
        else:
            token = generate_api_token()
            admin = User(
                username="admin",
                hashed_password=hash_password("admin"),
                role="admin",
                api_token=token,
                created_at=int(time.time() * 1000),
            )
            session.add(admin)
            await session.commit()
            print(f"Created admin user:")
            print(f"  Username: admin")
            print(f"  Password: admin")
            print(f"  API Token: {token}")
            print(f"  Role: admin")
            print()
            print("IMPORTANT: Change the default password in production!")

        # Create sample admission policy
        result = await session.execute(
            select(AdmissionPolicy).where(AdmissionPolicy.slug == "example-skill")
        )
        if not result.scalar_one_or_none():
            policy = AdmissionPolicy(
                slug="example-skill",
                policy_type="allow",
                approved_by="admin",
                approved_at=int(time.time() * 1000),
                notes="Sample admission policy - allows all versions of example-skill",
                created_at=int(time.time() * 1000),
            )
            session.add(policy)
            await session.commit()
            print("Created sample admission policy for 'example-skill'")

    await engine.dispose()
    print("\nSeed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
