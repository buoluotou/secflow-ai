"""Settings API — runtime configuration from the web UI.

LLM setup is intentionally ONE action: pick a vendor, paste the API key.
No .env editing, no service restart.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.organization import User
from app.services.audit import log_audit
from app.services.llm_config import (
    PROVIDER_PRESETS,
    clear_llm_config,
    get_llm_config,
    get_runtime_llm_config,
    mask_config,
    set_llm_config,
)
from ai.models.llm import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMSettingsIn(BaseModel):
    provider: str = Field(description="deepseek | openai | qwen | ollama | mock | custom")
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@router.get("/llm/providers")
def list_providers(_: User = Depends(get_current_user)) -> dict:
    return {"providers": PROVIDER_PRESETS}


@router.get("/llm")
def get_llm(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    runtime = get_runtime_llm_config(db)
    if runtime:
        return {"source": "runtime", **mask_config(runtime)}
    env = get_llm_config(db)
    return {
        "source": "env",
        "provider": env.provider,
        "model": env.model,
        "base_url": env.base_url,
        "api_key": "",
        "key_configured": bool(env.api_key),
    }


@router.post("/llm")
def save_llm(body: LLMSettingsIn, db: Session = Depends(get_db),
             user: User = Depends(require_admin)) -> dict:
    try:
        saved = set_llm_config(db, body.provider, body.api_key, body.base_url, body.model)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    log_audit(db, "settings.llm.update", "system", None,
              detail={"provider": body.provider}, username=user.username, user_id=user.id)
    return {"status": "saved", **saved}


@router.post("/llm/test")
def test_llm(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Test the REAL LLM endpoint. Mock mode has no endpoint — the response
    is honest about it instead of pretending the AI is connected."""
    cfg = get_llm_config(db)
    if cfg.provider == "mock":
        return {"ok": False, "status": "mock", "provider": "mock", "model": None,
                "error": "未接入真实模型（当前为 Mock 模式）— 请先选择服务商并配置密钥"}
    client = LLMClient(cfg)
    info = client.health()
    if info.get("ok"):
        return {"ok": True, "provider": client.provider, "model": client.config.model}
    return {"ok": False, "provider": client.provider,
            "model": client.config.model,
            "error": info.get("error", "连接失败")}


@router.delete("/llm")
def reset_llm(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> dict:
    clear_llm_config(db)
    log_audit(db, "settings.llm.reset", "system", None,
              username=user.username, user_id=user.id)
    return {"status": "reset", "message": "已恢复为环境变量配置（默认 mock）"}
