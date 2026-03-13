"""VULKRAN OS — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.routers import auth_router, clients_router, agent_router, notifications_router

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
    # Startup: create tables (dev convenience — use Alembic in production)
    logger.info("VULKRAN OS starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    # Shutdown
    await engine.dispose()
    logger.info("VULKRAN OS shut down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(agent_router)
app.include_router(notifications_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vulkran-os", "version": settings.app_version}


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "service": "vulkran-os", "version": settings.app_version}
