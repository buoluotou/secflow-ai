"""Runtime LLM configuration (web UI one-key setup, no restart needed).

Priority:
  1. system_settings['llm']  — set from the Settings page (provider + key)
  2. environment variables   — .env (LLM_PROVIDER / LLM_BASE_URL / ...)

Providers are pre-configured so the user only has to pick a vendor and
paste an API key:
  - deepseek : https://api.deepseek.com/v1        model deepseek-chat
  - openai   : https://api.openai.com/v1          model gpt-4o-mini
  - qwen     : https://dashscope.aliyuncs.com/compatible-mode/v1  model qwen-plus
  - ollama   : http://localhost:11434             model qwen2.5:7b
  - custom   : user-provided base_url + model
  - mock     : offline rule-based
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ai.models.config import LLMConfig
from app.models.analysis import SystemSetting

PROVIDER_PRESETS: dict[str, dict] = {
    "mock": {"base_url": "", "model": "", "needs_key": False, "label": "Mock 离线模式"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat",
                 "needs_key": True, "label": "DeepSeek"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
               "needs_key": True, "label": "OpenAI"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
             "model": "qwen-plus", "needs_key": True, "label": "通义千问"},
    "ollama": {"base_url": "http://localhost:11434", "model": "qwen2.5:7b",
               "needs_key": False, "label": "Ollama（本地）"},
    "custom": {"base_url": "", "model": "", "needs_key": True,
               "label": "自定义（OpenAI 兼容）"},
}


def get_runtime_llm_config(db: Session) -> dict | None:
    row = db.query(SystemSetting).filter(SystemSetting.key == "llm").first()
    return row.value if row else None


def get_llm_config(db: Session | None = None) -> LLMConfig:
    """Effective LLM config: runtime DB settings first, env vars as fallback."""
    runtime = None
    if db is not None:
        try:
            runtime = get_runtime_llm_config(db)
        except Exception:  # noqa: BLE001  (db not ready during bootstrap)
            runtime = None
    if runtime and runtime.get("provider"):
        preset = PROVIDER_PRESETS.get(runtime["provider"], {})
        return LLMConfig(
            provider=runtime["provider"],
            base_url=runtime.get("base_url") or preset.get("base_url", ""),
            api_key=runtime.get("api_key", ""),
            model=runtime.get("model") or preset.get("model", ""),
        )
    return LLMConfig.from_env()


def set_llm_config(db: Session, provider: str, api_key: str = "",
                   base_url: str = "", model: str = "") -> dict:
    """Persist LLM config from the Settings page (runtime, immediate).

    Validation is strict so the UI can never show a "connected" state that
    is not backed by a real endpoint + key:
      - preset vendors (deepseek/openai/qwen) REQUIRE an API key
      - custom requires base_url + model (key optional — private gateways)
      - mock / ollama need no key
    """
    if provider not in PROVIDER_PRESETS:
        raise ValueError(f"未知服务商: {provider}")
    preset = PROVIDER_PRESETS[provider]
    if provider == "custom":
        if not base_url or not model:
            raise ValueError("自定义服务商需要填写 Base URL 与模型名")
    elif preset.get("needs_key") and not api_key.strip():
        raise ValueError(f"{preset['label']} 需要填写 API 密钥")
    value = {
        "provider": provider,
        "api_key": api_key.strip() or "",
        "base_url": (base_url or preset["base_url"]).rstrip("/"),
        "model": model or preset["model"],
    }
    row = db.query(SystemSetting).filter(SystemSetting.key == "llm").first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key="llm", value=value))
    db.commit()
    return mask_config(value)


def clear_llm_config(db: Session) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == "llm").first()
    if row:
        db.delete(row)
        db.commit()


def mask_config(value: dict) -> dict:
    """Never expose the API key back to the frontend."""
    key = value.get("api_key", "")
    masked = f"{key[:4]}****{key[-4:]}" if len(key) > 8 else ("已设置" if key else "")
    return {**value, "api_key": masked, "key_configured": bool(key)}
