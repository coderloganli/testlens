from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_client import make_asgi_app
from redis.asyncio import Redis

from app.agent.agent import Agent
from app.agent.providers import build_provider
from app.agent.providers.base import LLMProvider
from app.api import router
from app.cache import QueryCache, SessionStore
from app.config import Settings, get_settings
from app.db import create_engine, create_sessionmaker
from app.observability import configure_logging, configure_tracing


def create_app(
    settings: Settings | None = None,
    redis: Redis | None = None,
    provider: LLMProvider | None = None,
) -> FastAPI:
    """Build the application. Tests inject Redis and the LLM provider; production builds both."""
    settings = settings or get_settings()
    configure_logging(settings)
    configure_tracing(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_engine(settings.database_url)
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        client = redis or Redis.from_url(settings.redis_url, decode_responses=True)
        sessionmaker = create_sessionmaker(engine)

        app.state.engine = engine
        app.state.sessionmaker = sessionmaker
        app.state.redis = client
        app.state.agent = Agent(
            provider=provider or build_provider(settings),
            sessionmaker=sessionmaker,
            query_cache=QueryCache(client, settings.query_cache_ttl_seconds),
            session_store=SessionStore(client, settings.session_ttl_seconds),
            max_steps=settings.agent_max_steps,
        )
        yield
        if redis is None:
            await client.aclose()
        await engine.dispose()

    app = FastAPI(title="TestLens API", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    app.mount("/metrics", make_asgi_app())
    FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz,readyz,metrics")
    RedisInstrumentor().instrument()
    return app
