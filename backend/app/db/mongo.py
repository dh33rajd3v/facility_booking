"""MongoDB client lifecycle and FastAPI dependencies."""

from typing import Any

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings


def create_client(settings: Settings) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        tz_aware=True,
    )


def get_db(request: Request) -> AsyncIOMotorDatabase:
    """FastAPI dependency returning the database attached to the app at startup."""
    return request.app.state.db


async def ping(db: Any) -> bool:
    """Return True when the database answers a ping."""
    try:
        await db.command("ping")
        return True
    except Exception:  # noqa: BLE001 - any failure means "not reachable" for health purposes
        return False


async def get_db_pinger(request: Request):
    """Dependency returning a zero-arg coroutine that checks DB reachability (overridable in tests)."""
    db = get_db(request)

    async def _ping() -> bool:
        return await ping(db)

    return _ping
