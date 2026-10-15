"""FastAPI application factory.

Run locally with:  uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import facilities, health
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.db.indexes import ensure_indexes
from app.db.mongo import create_client

API_PREFIX = "/api/v1"
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, database=None) -> FastAPI:
    """Build the app. Pass ``database`` (e.g. a mock) to skip connecting to MongoDB."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = None
        if database is None:
            client = create_client(settings)
            app.state.db = client[settings.mongodb_database]
            try:
                await ensure_indexes(app.state.db)
            except Exception:  # noqa: BLE001 - keep serving so /health can report the problem
                logger.warning("Could not ensure MongoDB indexes; is MongoDB running at the configured URI?")
        try:
            yield
        finally:
            if client is not None:
                client.close()

    app = FastAPI(title=settings.app_name, version="0.1.0-week1", lifespan=lifespan)
    if database is not None:
        app.state.db = database

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(facilities.router, prefix=API_PREFIX)
    return app


app = create_app()
