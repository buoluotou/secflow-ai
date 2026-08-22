"""Copilot API — the AI security assistant chat interface.

  GET  /api/copilot/tools  — tool list (quick-command buttons on the UI)
  POST /api/copilot/chat  — {message, history?} → {reply, tool, data}
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.organization import User
from app.services.copilot import TOOLS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["copilot"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] | None = None


@router.get("/tools")
def copilot_tools(_: User = Depends(get_current_user)) -> dict:
    return {"tools": [
        {"name": name, "label": label, "example": EXAMPLE.get(name, "")}
        for name, (label, _fn) in TOOLS.items()
    ]}


EXAMPLE = {
    "scan": "扫描 http://demo.local",
    "findings": "查看高危漏洞",
    "incidents": "应急响应，查看未处理事件",
    "audit": "审查今天的操作日志",
    "reports": "有哪些安全报告",
    "generate_report": "为最近的事件生成报告",
    "iocs": "查看威胁情报",
    "health": "系统健康检查",
    "security_advice": "系统安全吗？给防护建议",
    "help": "你能做什么",
}


@router.post("/chat")
def copilot_chat(body: ChatIn, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)) -> dict:
    """Agentic chat: the SecurityAgent reasons → acts → observes → answers.
    Returns the full reasoning trace (steps) so the UI can show HOW it worked.
    """
    try:
        from app.services.agent import SecurityAgent

        result = SecurityAgent(db).run(body.message)
        return {
            "reply": result.final_answer,
            "steps": [
                {
                    "thought": st.thought,
                    "action": st.action,
                    "result": st.result,
                    "ok": st.ok,
                }
                for st in result.steps
            ],
            "tool": result.tool,
            "data": result.data,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("copilot agent failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f"助手执行失败: {exc}") from exc
