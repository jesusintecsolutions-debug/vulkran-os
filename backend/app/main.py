"""VULKRAN OS — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.exceptions import register_error_handlers
from app.middleware import RateLimitMiddleware
from app.routers import auth_router, clients_router, agent_router, notifications_router, files_router, content_router

# Ensure all models are imported so Base.metadata knows about them
import app.models  # noqa: F401

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("vulkran")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VULKRAN OS v%s starting up...", settings.app_version)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    await engine.dispose()
    logger.info("VULKRAN OS shut down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Middleware (order matters: last added = first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)

# Error handlers
register_error_handlers(app)

# Routers
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(agent_router)
app.include_router(notifications_router)
app.include_router(files_router)
app.include_router(content_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vulkran-os", "version": settings.app_version}


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "service": "vulkran-os", "version": settings.app_version}
