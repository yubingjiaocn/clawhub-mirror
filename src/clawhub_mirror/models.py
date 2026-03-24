"""SQLAlchemy ORM models for ClawHub Mirror.

Defines all database tables using the modern mapped_column style with
DeclarativeBase. Timestamps are stored as epoch milliseconds (int).
"""

from __future__ import annotations

import time

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _now_ms() -> int:
    """Return current UTC time as epoch milliseconds."""
    return int(time.time() * 1000)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    """An authenticated user of the registry."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_api_token", "api_token"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="reader")
    api_token: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=_now_ms)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    skills: Mapped[list[Skill]] = relationship("Skill", back_populates="owner")


class Skill(Base):
    """A registered skill (Claude Code tool package)."""

    __tablename__ = "skills"
    __table_args__ = (
        Index("ix_skills_slug", "slug"),
        Index("ix_skills_owner_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    readme: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=_now_ms)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False, default=_now_ms)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    owner: Mapped[User] = relationship("User", back_populates="skills")
    versions: Mapped[list[SkillVersion]] = relationship(
        "SkillVersion", back_populates="skill"
    )


class SkillVersion(Base):
    """A specific version of a skill, pointing to a stored archive."""

    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_version"),
        Index("ix_skill_versions_skill_id", "skill_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=_now_ms)

    skill: Mapped[Skill] = relationship("Skill", back_populates="versions")


class AdmissionPolicy(Base):
    """An admission policy controlling which skills/versions are allowed."""

    __tablename__ = "admission_policies"
    __table_args__ = (Index("ix_admission_policies_slug", "slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    allowed_versions: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=_now_ms)


class PendingRequest(Base):
    """A request to add a skill to the registry, awaiting approval."""

    __tablename__ = "pending_requests"
    __table_args__ = (
        Index("ix_pending_requests_slug", "slug"),
        Index("ix_pending_requests_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[int] = mapped_column(Integer, nullable=False, default=_now_ms)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )


async def create_fts_tables(engine: AsyncEngine) -> None:
    """Create FTS5 virtual table and sync triggers for full-text skill search.

    This must be called after the regular tables have been created, since the
    FTS content table references the skills table.

    Args:
        engine: The async SQLAlchemy engine.
    """
    statements = [
        text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS skill_fts "
            "USING fts5(slug, display_name, summary, content=skills, content_rowid=id);"
        ),
        text(
            "CREATE TRIGGER IF NOT EXISTS skill_fts_insert AFTER INSERT ON skills BEGIN "
            "INSERT INTO skill_fts(rowid, slug, display_name, summary) "
            "VALUES (new.id, new.slug, new.display_name, new.summary); "
            "END;"
        ),
        text(
            "CREATE TRIGGER IF NOT EXISTS skill_fts_update AFTER UPDATE ON skills BEGIN "
            "INSERT INTO skill_fts(skill_fts, rowid, slug, display_name, summary) "
            "VALUES ('delete', old.id, old.slug, old.display_name, old.summary); "
            "INSERT INTO skill_fts(rowid, slug, display_name, summary) "
            "VALUES (new.id, new.slug, new.display_name, new.summary); "
            "END;"
        ),
        text(
            "CREATE TRIGGER IF NOT EXISTS skill_fts_delete AFTER DELETE ON skills BEGIN "
            "INSERT INTO skill_fts(skill_fts, rowid, slug, display_name, summary) "
            "VALUES ('delete', old.id, old.slug, old.display_name, old.summary); "
            "END;"
        ),
    ]

    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(stmt)
