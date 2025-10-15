"""Alembic environment configuration for async SQLAlchemy."""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.shared.database import Base  # noqa: F401
from src.shared.models import *  # noqa: F401, F403 — ensure all models are registered

target_metadata = Base.metadata

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ecosupplyai:ecosupplyai@localhost:5432/ecosupplyai",
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without a live DB)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an async engine."""
    connectable = create_async_engine(DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
