from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.processing_jobs import get_processing_dispatcher

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings_provider = application.dependency_overrides.get(get_settings, get_settings)
    dispatcher_provider = application.dependency_overrides.get(
        get_processing_dispatcher, get_processing_dispatcher
    )
    active_settings = settings_provider()
    dispatcher = dispatcher_provider()
    logger.info("Starting ClimbIQ API version %s", active_settings.app_version)
    try:
        dispatcher.recover(active_settings)
    except Exception:
        logger.exception("Could not recover interrupted pose-processing jobs")
    try:
        yield
    finally:
        dispatcher.shutdown()
        logger.info("Stopping ClimbIQ API")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local-first video ingestion and climbing movement analysis API.",
    lifespan=lifespan,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)
if settings.trusted_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_timing(request: Request, call_next):  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.perf_counter() - started:.6f}"
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(api_router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    payload = {"name": settings.app_name, "health": "/api/health"}
    if settings.environment != "production":
        payload["docs"] = "/docs"
    return payload
