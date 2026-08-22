"""Health API (spec §48).

Responses are tri-state so dashboards can distinguish a real outage from a
service that is simply not configured yet:

    {"ok": true,  "status": "ok"}
    {"ok": false, "status": "not_configured", "error": "..."}
    {"ok": false, "status": "error",          "error": "..."}
"""
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


def _tri(state: str, ok: bool, error: str | None = None) -> dict:
    return {"ok": ok, "status": state, "error": error}


@router.get("")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@router.get("/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return _tri("ok", True)
    except Exception as exc:  # noqa: BLE001
        return _tri("error", False, str(exc))


@router.get("/redis")
def health_redis() -> dict:
    try:
        _redis().ping()
        return _tri("ok", True)
    except Exception as exc:  # noqa: BLE001
        return _tri("error", False, str(exc))


@router.get("/wazuh")
def health_wazuh() -> dict:
    if not settings.wazuh_url:
        return _tri("not_configured", False,
                    "WAZUH_URL 未配置 — 可选组件，配置后自动同步告警 (docs/deployment.md)")
    from integrations.wazuh.client import WazuhClient

    try:
        info = WazuhClient().health()
        return _tri("ok" if info.get("ok") else "error", info.get("ok", False),
                    info.get("error") if not info.get("ok") else None)
    except Exception as exc:  # noqa: BLE001
        return _tri("error", False, str(exc))


@router.get("/misp")
def health_misp() -> dict:
    if not settings.misp_url or not settings.misp_api_key:
        return _tri("not_configured", False,
                    "MISP_URL / MISP_API_KEY 未配置 — 可选组件，配置后提供威胁情报 (docs/deployment.md)")
    from integrations.misp.client import MISPClient

    try:
        info = MISPClient().health()
        return _tri("ok" if info.get("ok") else "error", info.get("ok", False),
                    info.get("error") if not info.get("ok") else None)
    except Exception as exc:  # noqa: BLE001
        return _tri("error", False, str(exc))


@router.get("/llm")
def health_llm() -> dict:
    info = LLMClient().health()
    return _tri("ok" if info.get("ok") else "error", info.get("ok", False),
                info.get("error") if not info.get("ok") else None)


@router.get("/config")
def health_config(_: Session = Depends(get_db)) -> dict:
    """Non-sensitive configuration summary (for the frontend setup wizard)."""
    return {
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.llm_model or _default_model_hint(),
            "base_url": settings.llm_base_url or "",
            "configured": bool(settings.llm_base_url) if settings.llm_provider != "mock" else True,
        },
        "wazuh": {"configured": bool(settings.wazuh_url)},
        "misp": {"configured": bool(settings.misp_url and settings.misp_api_key)},
        "nuclei": {"mode": settings.nuclei_mode},
        "env": settings.app_env,
    }


def _default_model_hint() -> str:
    if settings.llm_provider == "ollama":
        return "qwen2.5:7b"
    return "gpt-4o-mini"
