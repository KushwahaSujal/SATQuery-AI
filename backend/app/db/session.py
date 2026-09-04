"""
SatQuery AI — Async PostgreSQL Database Engine & Session Management
"""
import os
import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.config import settings
from backend.app.logging import logger

_async_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None
_engine_loop = None


def _is_transaction_pooler(db_url: str) -> bool:
    """
    Heuristically detects a transaction-mode connection pooler in front of PostgreSQL.

    Transaction/statement pooling (pgBouncer and hosted equivalents such as Supabase's
    pooler on port 6543) rebinds each transaction to an arbitrary server connection, so
    server-side prepared statements leak across clients and asyncpg raises
    DuplicatePreparedStatementError. Callers use this to disable the statement cache.

    Override with SATQUERY_DB_POOLER=1 / 0 when the heuristic guesses wrong.
    """
    override = os.getenv("SATQUERY_DB_POOLER")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes")

    host_part = db_url.split("@")[-1].lower()
    # Port 6543 is the conventional transaction-pooling port (Supabase, Neon, PgCat).
    # Deliberately NOT matching "pooler." alone: the same pooler host on :5432 is
    # session mode, which supports prepared statements normally (verified 2026-09-04),
    # and disabling the cache there would cost performance for no benefit.
    return ":6543" in host_part or "pgbouncer" in host_part


def get_database_url() -> str:
    """Returns database connection URL, ensuring asyncpg driver is specified for PostgreSQL, with safe test fallback."""
    is_test_env = (
        settings.app.environment == "test"
        or os.getenv("SATQUERY_ENV") == "test"
        or "pytest" in sys_modules_check()
    )
    if is_test_env and os.getenv("SATQUERY_USE_POSTGRES_IN_TESTS", "0") != "1":
        from pathlib import Path
        Path("results").mkdir(parents=True, exist_ok=True)
        return "sqlite+aiosqlite:///results/satquery_test.db"

    url = settings.database.url
    # Ensure URL starts with postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def get_async_engine() -> AsyncEngine:
    """Singleton getter for SQLAlchemy 2.0 AsyncEngine, scoped to the current event loop."""
    global _async_engine, _session_maker, _engine_loop

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    # Recreate engine if event loop changed (e.g. across pytest-asyncio tests)
    if (
        _async_engine is None
        or (_engine_loop is not None and current_loop is not None and _engine_loop != current_loop)
    ):
        _engine_loop = current_loop
        db_url = get_database_url()
        safe_url = db_url.split("@")[-1] if "@" in db_url else "database"
        logger.debug(f"Initializing SQLAlchemy async engine for @{safe_url}")

        engine_kwargs = {
            "echo": settings.database.echo,
            "future": True,
        }

        # Use NullPool in testing or if explicitly requested to prevent cross-loop connection sharing
        is_test_env = (
            settings.app.environment == "test"
            or os.getenv("SATQUERY_ENV") == "test"
            or "pytest" in sys_modules_check()
        )

        if is_test_env:
            engine_kwargs["poolclass"] = NullPool
        elif "postgresql" in db_url:
            engine_kwargs.update({
                "pool_size": settings.database.pool_size,
                "max_overflow": settings.database.max_overflow,
                "pool_timeout": settings.database.pool_timeout,
                "pool_pre_ping": True,
            })

            # Transaction-mode connection poolers (pgBouncer, Supabase :6543, PgCat)
            # multiplex many clients onto few server connections, so a prepared
            # statement created by one client can collide with another's:
            #   asyncpg.exceptions.DuplicatePreparedStatementError:
            #   prepared statement "__asyncpg_stmt_1__" already exists
            # Disabling asyncpg's statement cache is the supported workaround.
            # Verified 2026-09-04: without this, Supabase :6543 fails on the second
            # parameterised query; with it, all probes pass. See decisions.md D-113.
            if _is_transaction_pooler(db_url):
                engine_kwargs["connect_args"] = {
                    **engine_kwargs.get("connect_args", {}),
                    "statement_cache_size": 0,
                    "prepared_statement_cache_size": 0,
                }
                logger.info(
                    "Transaction-mode pooler detected; asyncpg prepared-statement "
                    "cache disabled to prevent DuplicatePreparedStatementError."
                )

        _async_engine = create_async_engine(db_url, **engine_kwargs)
        if "sqlite" in db_url:
            from sqlalchemy import event
            @event.listens_for(_async_engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _session_maker = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _async_engine


def sys_modules_check() -> list:
    import sys
    return list(sys.modules.keys())


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Getter for async_sessionmaker bound to the current engine."""
    get_async_engine()
    return _session_maker


async def ensure_db_tables():
    """Ensures database tables exist (creates schema for SQLite test/fallback environments)."""
    engine = get_async_engine()
    from backend.app.db.base import Base
    import backend.app.db.models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_db_engine():
    """Application startup hook: initializes engine and tests connectivity."""
    engine = get_async_engine()
    try:
        if "sqlite" in str(engine.url):
            await ensure_db_tables()
            logger.info("SQLite fallback database initialized and verified.")
            return

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL database connection initialized and verified.")
    except Exception as e:
        logger.warning(f"Database connection could not be established at startup: {e}")


async def dispose_db_engine():
    """Application shutdown hook: cleanly disposes connection pool."""
    global _async_engine, _session_maker, _engine_loop
    if _async_engine is not None:
        logger.info("Disposing SQLAlchemy async engine connection pool...")
        await _async_engine.dispose()
        _async_engine = None
        _session_maker = None
        _engine_loop = None
        logger.info("SQLAlchemy async engine disposed.")


async def check_database_connection() -> bool:
    """Health check helper: returns True if database can execute query."""
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.debug(f"Database check failed: {e}")
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated AsyncSession per request."""
    session_factory = get_session_maker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
