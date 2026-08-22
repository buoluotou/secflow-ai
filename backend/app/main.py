"""SecFlow AI backend entrypoint.

Run (dev):
    uvicorn app.main:app --reload --port 8000

See docs/development.md for the full local workflow.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.logging import get_logger, new_request_id, setup_logging
from app.db.seed import seed_admin, seed_demo_data

setup_logging(service="secflow-api")
logger = get_logger("secflow.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev bootstrap: create tables + seed admin & demo data.
    # Production deployments use Alembic migrations instead.
    from app.core.database import init_db

    init_db()
    try:
        seed_admin()
        if settings.app_env == "development":
            seed_demo_data()
    except Exception as exc:  # noqa: BLE001
        logger.warning("seed failed (continuing): %s", exc)
    yield


app = FastAPI(
    title="SecFlow AI API",
    description="AI-Powered Security Service Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost", "http://localhost:5173", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Structured JSON access log with request_id (spec §49)."""
    request_id = new_request_id()
    request.state.request_id = request_id
    logger.info(
        "request",
        extra={"extra_fields": {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }},
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }


app.include_router(api_router)
