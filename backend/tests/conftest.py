from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient

from app.agent.providers.fake import FakeProvider
from app.config import Settings
from app.db import create_engine, create_sessionmaker
from app.main import create_app
from app.seed import seed

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    """A fresh SQLite database migrated to head with the project's Alembic migrations."""
    url = f"sqlite+aiosqlite:///{(tmp_path / 'testlens.db').as_posix()}"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    return url


@pytest.fixture
async def sessionmaker(database_url: str):
    engine = create_engine(database_url)
    maker = create_sessionmaker(engine)
    async with maker() as session:
        await seed(session)
    yield maker
    await engine.dispose()


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
async def client(sessionmaker, database_url: str, redis: FakeAsyncRedis, provider):
    settings = Settings(database_url=database_url, log_json=False)
    app = create_app(settings=settings, redis=redis, provider=provider)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
