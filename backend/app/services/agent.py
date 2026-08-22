"""Security Agent — a real ReAct (Reason+Act) agent, not a single intent match.

The agent LOOKS at the task, THINKS about what to do, CALLS tools, OBSERVES
the results and continues — exactly like a human security engineer (or this
assistant) would, until it can answer. Complex tasks such as "全面巡检并出报告"
are decomposed and executed autonomously.

Loop (max MAX_ITER steps):
  state = task + tool results so far
  LLM emits JSON: {"thought","action","action_input"} or {"final_answer"}
  execute tool → append result → next round

Safety boundary (project principle §5): dangerous operations (block IP,
delete data, auto-approve) are NEVER auto-executed — the agent may only
recommend them for human approval.

Mock mode: a rule-based planner reproduces the same multi-step behaviour
offline (no API key needed), so the agentic UX is always available.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ai.models.llm import LLMClient, LLMError
from app.services.llm_config import get_llm_config

logger = logging.getLogger(__name__)

MAX_ITER = 6

AGENT_SYSTEM_PROMPT = """你是 SecFlow AI 的智能安全运营 Agent，一名资深安全工程师的数字化分身。
用户会下达安全任务（可能复杂、多步）。你必须像真实工程师一样：
1. 先思考（thought）：分析任务需要哪些步骤、需要哪些信息
2. 逐步行动（action/action_input）：每次只调用一个工具
3. 观察工具结果后继续思考，直到能给出最终答案（final_answer）
复杂任务要拆解。例如"全面安全巡检"应依次调用 health → incidents → findings → audit，再汇总。

可用工具（每次 action 只能选一个）：
- scan: {"targets": ["目标"], "severity": "可选"} —— 发起漏洞扫描
- findings: {"severity": "可选","status": "可选"} —— 查询漏洞
- incidents: {"open_only": true} —— 查询安全事件（应急响应）
- audit: {} —— 审查操作日志（统计）
- iocs: {} —— 查询威胁情报
- reports: {} —— 查询已有报告
- analyze_incident: {"incident_id": "id"} —— 对事件执行 AI 研判（分类/风险/建议）
- generate_report: {"incident_id": "可选", "report_type": "incident|vulnerability"} —— 生成安全报告
- health: {} —— 系统健康检查
- security_advice: {} —— 综合防护建议

严格规则：
- 只输出一个 JSON，二选一：
  {"thought": "思考", "action": "工具名", "action_input": {...}}
  或
  {"final_answer": "给用户的最终回答（中文，简洁专业，引用关键数据与下一步建议）"}
- 不允许编造工具结果中没有的事实
- 危险操作（封禁 IP、删除数据、自动批准）只能作为建议文字给出，绝不调用工具执行
- 若工具结果不足，继续调用其他工具补全信息，最多 6 步"""


@dataclass
class AgentStep:
    thought: str
    action: str | None = None
    action_input: dict = field(default_factory=dict)
    result: str | None = None
    ok: bool = True


@dataclass
class AgentResult:
    final_answer: str
    steps: list[AgentStep] = field(default_factory=list)
    tool: str | None = None
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool layer (shared with the copilot; returns (ok, summary, data))
# ---------------------------------------------------------------------------
def _run_tool(db: Session, name: str, args: dict) -> tuple[bool, str, dict]:
    from app.services.copilot import TOOLS

    if name not in TOOLS:
        return False, f"未知工具: {name}", {}
    fn = TOOLS[name][1]
    res = fn(db, args)  # type: ignore[operator]
    return res.ok, res.summary, res.data


class SecurityAgent:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMClient(get_llm_config(db))

    # ------------------------------------------------------------------
    def run(self, task: str) -> AgentResult:
        steps: list[AgentStep] = []
        state: list[dict] = []

        for i in range(MAX_ITER):
            decision = self._decide(task, state)
            if "final_answer" in decision:
                return AgentResult(
                    final_answer=decision["final_answer"],
                    steps=steps,
                    tool=steps[-1].action if steps else None,
                    data=steps[-1].action_input if steps else {},
                )
            action = str(decision.get("action", "")).strip()
            args = decision.get("action_input") if isinstance(decision.get("action_input"), dict) else {}
            thought = str(decision.get("thought", ""))[:200]

            if action == "final_answer":
                return AgentResult(final_answer=str(decision.get("final_answer", "完成")), steps=steps)

            ok, summary, data = _run_tool(self.db, action, args)
            step = AgentStep(thought=thought, action=action, action_input=args,
                             result=summary[:300], ok=ok)
            steps.append(step)
            state.append({"step": i + 1, "action": action, "thought": thought,
                          "result": summary[:300], "data": data, "ok": ok})

        # loop exhausted — summarize what was done
        return AgentResult(
            final_answer="已完成多步分析（达到步骤上限）。请查看上方执行过程，或让我继续针对某个结果深入处理。",
            steps=steps,
        )

    # ------------------------------------------------------------------
    def _decide(self, task: str, state: list[dict]) -> dict:
        if self.llm.config.transport != "mock":
            try:
                payload = json.dumps(
                    {"task": task, "executed_steps": state},
                    ensure_ascii=False, default=str,
                )
                return self.llm.complete_json(AGENT_SYSTEM_PROMPT, payload)
            except (LLMError, json.JSONDecodeError):
                logger.warning("agent LLM decision failed, using rule planner")
        return self._rule_decide(task, state)

    # ------------------------------------------------------------------
    def _rule_decide(self, task: str, state: list[dict]) -> dict:
        """Offline planner — reproduces multi-step reasoning for common tasks."""
        done = {s["action"] for s in state}
        low = task.lower()

        # 全面巡检 / 安全检查 / 保障系统安全
        if any(k in task for k in ("巡检", "全面检查", "安全检查", "保障", "评估")):
            if "health" not in done:
                return {"thought": "先检查系统健康状态", "action": "health", "action_input": {}}
            if "incidents" not in done:
                return {"thought": "再查看未处理安全事件", "action": "incidents", "action_input": {"open_only": True}}
            if "findings" not in done:
                return {"thought": "查看高危漏洞情况", "action": "findings", "action_input": {"status": "open"}}
            if "audit" not in done:
                return {"thought": "审查操作日志", "action": "audit", "action_input": {}}
            return {"final_answer": "巡检完成：健康、事件、漏洞、日志均已核查（见上方执行过程）。需要我为这些问题生成一份巡检报告吗？"}

        # 应急响应 / 处置
        if any(k in task for k in ("应急", "处置", "响应", "处理事件")):
            if "incidents" not in done:
                return {"thought": "先列出待处理事件", "action": "incidents", "action_input": {"open_only": True}}
            if "analyze_incident" not in done:
                if _first_incident_id(state):
                    return {"thought": "对首要事件执行 AI 研判", "action": "analyze_incident",
                            "action_input": {"incident_id": _first_incident_id(state)}}
                return {"final_answer": "当前没有待处理事件。可先发起扫描或注入告警产生事件。"}
            return {"final_answer": "应急响应完成：已列出事件并对首要事件完成 AI 研判（分类/风险/建议见上方）。请到「事件响应」页完成人工审核与闭环。"}

        # 扫描
        if any(k in task for k in ("扫描", "nuclei", "扫")):
            if "scan" not in done:
                return {"thought": "解析目标并发起扫描", "action": "scan",
                        "action_input": {"targets": _extract_targets(task)}}
            if "findings" not in done:
                return {"thought": "扫描已发起，确认漏洞记录", "action": "findings", "action_input": {}}
            return {"final_answer": "扫描任务已发起（后台执行），并已确认当前漏洞记录。完成后漏洞会自动入库并尝试关联安全事件，可稍后在「漏洞管理」查看。"}

        # 报告
        if any(k in task for k in ("报告", "撰写", "巡检报告", "write")):
            if "findings" not in done:
                return {"thought": "先汇总漏洞情况用于报告", "action": "findings", "action_input": {}}
            if "incidents" not in done:
                return {"thought": "再汇总安全事件", "action": "incidents", "action_input": {"open_only": True}}
            if "generate_report" not in done:
                return {"thought": "数据齐备，生成综合报告", "action": "generate_report", "action_input": {}}
            if state and not state[-1].get("ok", True):
                return {"final_answer": "当前没有可生成报告的事件（无漏洞/事件数据）。可先发起扫描：例如“扫描 http://demo.local”，或注入告警后重试。"}
            return {"final_answer": "报告已生成，可在「安全报告」页查看并下载 PDF。"}

        # 漏洞
        if any(k in task for k in ("漏洞", "vuln")):
            if "findings" not in done:
                return {"thought": "查询漏洞", "action": "findings",
                        "action_input": {"severity": _severity(task)}}
            return {"final_answer": "漏洞查询完成，结果见上方。可让我生成漏洞修复优先级排序或报告。"}

        # 日志审查
        if any(k in task for k in ("日志", "审查", "审计")):
            if "audit" not in done:
                return {"thought": "审查操作日志", "action": "audit", "action_input": {}}
            return {"final_answer": "日志审查完成：统计结果见上方，可在「日志审查」页筛选与导出。"}

        # 健康
        if any(k in task for k in ("健康", "状态", "正常吗")):
            if "health" not in done:
                return {"thought": "检查系统健康", "action": "health", "action_input": {}}
            return {"final_answer": "健康检查完成，各组件状态见上方。"}

        # 安全防护建议
        if any(k in task for k in ("防护", "建议", "加固", "保障", "安全吗", "安全服务")):
            if "security_advice" not in done:
                return {"thought": "综合评估并给出防护建议", "action": "security_advice", "action_input": {}}
            return {"final_answer": "防护建议已给出（见上方）。可让我继续执行，例如“全面安全巡检”或“生成巡检报告”。"}

        # 默认：引导
        return {"thought": "先给出能力引导", "action": "help", "action_input": {}}


def _has_incidents(state: list[dict]) -> bool:
    for s in state:
        if s["action"] == "incidents":
            return bool((s.get("data") or {}).get("incidents"))
    return False


def _first_incident_id(state: list[dict]) -> str:
    for s in state:
        if s["action"] == "incidents":
            incs = (s.get("data") or {}).get("incidents") or []
            if incs:
                return incs[0].get("id", "")
    return ""


def _extract_targets(task: str) -> list[str]:
    import re

    return re.findall(
        r"(?:https?://)?[a-zA-Z0-9][a-zA-Z0-9.-]*\.(?:com|net|org|io|cn|local|xyz|top|dev)(?:[:/][^\s,，；]*)?"
        r"|\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?"
        r"|https?://[^\s,，；]+",
        task,
    )[:5]


def _severity(task: str) -> str:
    for s in ("critical", "high", "medium", "low"):
        if s in task.lower():
            return s
    return ""
