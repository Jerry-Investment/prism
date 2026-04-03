"""Database connection pool management."""
import asyncpg
import psycopg2
from contextlib import asynccontextmanager, contextmanager
from loguru import logger

from config import settings

_async_pool: asyncpg.Pool | None = None


async def get_async_pool() -> asyncpg.Pool:
    global _async_pool
    if _async_pool is None:
        _async_pool = await asyncpg.create_pool(
            settings.db_dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Async DB pool created")
    return _async_pool


async def close_async_pool() -> None:
    global _async_pool
    if _async_pool:
        await _async_pool.close()
        _async_pool = None
        logger.info("Async DB pool closed")


@asynccontextmanager
async def async_conn():
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        yield conn


@contextmanager
def sync_conn():
    conn = psycopg2.connect(settings.db_dsn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


async def apply_schema() -> None:
    """Run schema.sql against the database (idempotent)."""
    import pathlib
    sql = (pathlib.Path(__file__).parent / "schema.sql").read_text()
    async with async_conn() as conn:
        await conn.execute(sql)
    logger.info("Schema applied")
