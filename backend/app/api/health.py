"""Health API (spec §48)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from ai.models.llm import LLMClient

router = APIRouter(prefix="/health", tags=["health"])


def _redis():
    return Redis.from_url(settings.redis_url, socket_timeout=3, decode_responses=True)


@router.get("")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@router.get("/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@router.get("/redis")
def health_redis() -> dict:
    try:
        _redis().ping()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@router.get("/wazuh")
def health_wazuh() -> dict:
    from integrations.wazuh.client import WazuhClient

    return WazuhClient().health()


@router.get("/misp")
def health_misp() -> dict:
    from integrations.misp.client import MISPClient

    return MISPClient().health()


@router.get("/llm")
def health_llm() -> dict:
    return LLMClient().health()
