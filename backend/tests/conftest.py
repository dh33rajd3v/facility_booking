import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.db.indexes import ensure_indexes
from app.db.mongo import get_db_pinger
from app.db.seed import seed_all
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", mongodb_database="facility_booking_test")


@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client["facility_booking_test"]
    await ensure_indexes(database)
    return database


@pytest.fixture
async def seeded_db(db):
    await seed_all(db)
    return db


def _make_client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(settings, seeded_db):
    app = create_app(settings=settings, database=seeded_db)

    async def healthy():
        return True

    app.dependency_overrides[get_db_pinger] = lambda: healthy
    async with _make_client(app) as http:
        yield http


@pytest.fixture
async def unhealthy_client(settings, db):
    app = create_app(settings=settings, database=db)

    async def unhealthy():
        return False

    app.dependency_overrides[get_db_pinger] = lambda: unhealthy
    async with _make_client(app) as http:
        yield http
