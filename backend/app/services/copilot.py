"""AI Security Copilot — the flagship chat interface (安服·AI 助手).

The user talks to the platform in natural language ("扫描 10.10.10.10",
"审查今天的日志", "应急响应") and the copilot:
  1. resolves intent → picks a tool (+ args)
  2. executes the tool against the live system
  3. asks the LLM (or rule templates in mock mode) to summarize the result

Tool registry is the security-service surface: scan / findings / incidents /
audit / reports / iocs / health / security_advice — everything an 安服
engineer does during a task.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ai.models.llm import LLMClient, LLMError
from app.core.config import settings
from app.services.llm_config import get_llm_config
from app.services.audit import log_audit

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """你是 SecFlow AI 安全助手 Copilot 的意图解析器。
用户会用中文下达安全任务指令。请把指令解析为 JSON：
{"tool": "工具名", "args": {...}, "reasoning": "一句话说明"}
工具列表(只可选其一):
- scan: 发起漏洞扫描. args: {"targets": ["目标URL或IP"], "severity": "可选 high/medium/low"}
- findings: 查询漏洞. args: {"severity": "可选", "status": "可选"}
- incidents: 查询安全事件. args: {"status": "可选 open/closed", "severity": "可选"}
- audit: 日志审查(操作日志统计). args: {}
- reports: 查询已生成的安全报告. args: {}
- generate_report: 为某个事件生成安全报告. args: {"incident_id": "事件ID(如用户提到)"}
- iocs: 查询威胁情报. args: {}
- health: 系统健康检查. args: {}
- security_advice: 综合安全防护建议. args: {}
- help: 用户打招呼/询问能力/意图不明. args: {}
只输出 JSON，不要其他文字。"""

REPLY_SYSTEM_PROMPT = """你是 SecFlow AI 安全助手 Copilot，一名资深安全运营工程师。
用户下达了安全任务，工具已执行完毕。请用简洁专业的中文向用户汇报：
1. 做了什么、结果如何（引用关键数据，如发现几个漏洞、事件数量、风险等级）
2. 下一步建议（1-3 条具体可执行动作）
不要编造工具结果之外的事实。结果数据在下方 JSON 中。"""


@dataclass
class ToolResult:
    ok: bool
    summary: str
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool registry — each tool is a function(db, args) -> ToolResult
# ---------------------------------------------------------------------------
def _tool_scan(db: Session, args: dict) -> ToolResult:
    from app.models.analysis import ScanJob
    from app.models.project import Project

    targets = args.get("targets") or []
    if isinstance(targets, str):
        targets = [t.strip() for t in re.split(r"[\n,;，；]", targets) if t.strip()]
    if not targets:
        return ToolResult(False, "请提供扫描目标，例如：扫描 10.10.10.10 或 http://demo.local")
    project = db.query(Project).first()
    if not project:
        project = Project(name="默认项目", description="Copilot 自动创建")
        db.add(project)
        db.flush()
    job = ScanJob(project_id=project.id, scan_type="nuclei", targets=targets,
                  options={"severity": args.get("severity") or "high"},
                  status="queued", created_by="copilot")
    db.add(job)
    db.flush()
    try:
        from app.workers.tasks import run_nuclei_scan

        run_nuclei_scan.delay(job.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("copilot scan enqueue failed: %s", exc)
    db.commit()
    return ToolResult(True, f"已发起漏洞扫描（{len(targets)} 个目标）", {"scan_id": job.id, "targets": targets})


def _tool_findings(db: Session, args: dict) -> ToolResult:
    from app.models.security import Finding

    q = db.query(Finding)
    if args.get("severity"):
        q = q.filter(Finding.severity == args["severity"])
    if args.get("status"):
        q = q.filter(Finding.status == args["status"])
    items = q.order_by(Finding.last_seen.desc()).limit(20).all()
    if not items:
        return ToolResult(True, "当前没有符合条件的漏洞记录", {"findings": []})
    summary = f"共 {len(items)} 条漏洞，按严重性: " + ", ".join(
        f"{s}={sum(1 for f in items if f.severity == s)}"
        for s in ("critical", "high", "medium", "low")
        if any(f.severity == s for f in items)
    )
    return ToolResult(True, summary, {
        "findings": [{"template_id": f.template_id, "title": f.title,
                      "severity": f.severity, "status": f.status} for f in items]})


def _tool_incidents(db: Session, args: dict) -> ToolResult:
    from app.models.incident import Incident

    q = db.query(Incident)
    if args.get("status"):
        q = q.filter(Incident.status == args["status"])
    elif args.get("open_only"):
        q = q.filter(Incident.status.notin_(["closed", "resolved"]))
    if args.get("severity"):
        q = q.filter(Incident.severity == args["severity"])
    items = q.order_by(Incident.detected_at.desc()).limit(20).all()
    if not items:
        return ToolResult(True, "当前没有安全事件", {"incidents": []})
    open_n = sum(1 for i in items if i.status not in ("closed", "resolved"))
    high_n = sum(1 for i in items if i.severity in ("high", "critical"))
    return ToolResult(True, f"共 {len(items)} 条事件（未闭环 {open_n}，高危 {high_n}）", {
        "incidents": [{"id": i.id, "title": i.title, "severity": i.severity,
                       "status": i.status, "confidence": i.confidence} for i in items]})


def _tool_audit(db: Session, args: dict) -> ToolResult:
    from app.models.analysis import AuditLog

    items = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(500).all()
    if not items:
        return ToolResult(True, "暂无操作日志", {"stats": {}})
    stats: dict = {}
    users: dict = {}
    for i in items:
        cat = i.action.split(".")[0] or "other"
        stats[cat] = stats.get(cat, 0) + 1
        users[i.username or "system"] = users.get(i.username or "system", 0) + 1
    top = sorted(stats.items(), key=lambda kv: kv[1], reverse=True)
    summary = "日志审查结果：" + "；".join(f"{k} {v} 次" for k, v in top[:6])
    return ToolResult(True, summary, {"stats": stats, "users": dict(sorted(users.items(), key=lambda kv: kv[1], reverse=True)[:5])})


def _tool_reports(db: Session, args: dict) -> ToolResult:
    from app.models.analysis import Report

    items = db.query(Report).order_by(Report.created_at.desc()).limit(10).all()
    if not items:
        return ToolResult(True, "暂无报告 —— 可在事件详情页生成，或让我为指定事件生成", {"reports": []})
    return ToolResult(True, f"共有 {len(items)} 份报告", {
        "reports": [{"id": r.id, "title": r.title, "type": r.report_type,
                     "status": r.status, "created_at": str(r.created_at)} for r in items]})


def _tool_generate_report(db: Session, args: dict) -> ToolResult:
    from app.models.incident import Incident
    from app.services.reports import ReportService

    incident_id = args.get("incident_id")
    incident = db.get(Incident, incident_id) if incident_id else db.query(Incident).first()
    if not incident:
        return ToolResult(False, "没有可生成报告的事件。请先发起扫描或注入告警产生事件，或指定事件 ID")
    report = ReportService(db).generate_incident_report(incident, created_by="copilot")
    db.commit()
    return ToolResult(True, f"报告已生成：《{report.title}》（PDF 可下载）",
                      {"report_id": report.id, "title": report.title})


def _tool_analyze_incident(db: Session, args: dict) -> ToolResult:
    from app.models.incident import Incident
    from app.services.analysis import AnalysisService

    incident_id = args.get("incident_id")
    incident = db.get(Incident, incident_id) if incident_id else db.query(Incident).first()
    if not incident:
        return ToolResult(False, "没有可分析的事件，请先产生事件（扫描或告警）")
    results = AnalysisService(db).analyze_incident(incident, force=True)
    db.commit()
    triage = results.get("triage") or {}
    risk = results.get("risk") or {}
    return ToolResult(
        True,
        f"AI 研判完成：{triage.get('classification', '—')} / {triage.get('severity', '—')}"
        f"，风险 {risk.get('risk_score', '—')}（{risk.get('risk_level', '—')}）",
        {"incident_id": incident.id, "classification": triage.get("classification"),
         "severity": triage.get("severity"), "risk_score": risk.get("risk_score"),
         "risk_level": risk.get("risk_level"),
         "recommendations": triage.get("recommendations", [])},
    )


def _tool_iocs(db: Session, args: dict) -> ToolResult:
    from app.models.security import IOC

    items = db.query(IOC).order_by(IOC.last_seen.desc()).limit(10).all()
    if not items:
        return ToolResult(True, "暂无威胁情报 IOC —— 可在「事件响应 → 威胁情报」添加", {"iocs": []})
    return ToolResult(True, f"共 {len(items)} 条威胁情报",
                      {"iocs": [{"type": i.type, "value": i.value, "confidence": i.confidence} for i in items]})


def _tool_health(db: Session, args: dict) -> ToolResult:
    from app.api.health import health_db, health_redis
    from app.services.llm_config import get_llm_config

    cfg = get_llm_config(db)
    db_ok = health_db(db).get("ok")
    redis_ok = health_redis().get("ok")
    lines = [
        f"数据库: {'正常' if db_ok else '异常'}",
        f"Redis: {'正常' if redis_ok else '异常'}",
        f"AI: {'Mock 模式（未接入真实模型）' if cfg.provider == 'mock' else f'已接入 {cfg.provider}'}",
        f"Wazuh: {'已配置' if settings.wazuh_url else '未配置（可选）'}",
        f"MISP: {'已配置' if settings.misp_url and settings.misp_api_key else '未配置（可选）'}",
    ]
    return ToolResult(True, "；".join(lines), {"db": db_ok, "redis": redis_ok, "llm": cfg.provider})


def _tool_advice(db: Session, args: dict) -> ToolResult:
    """综合安全防护建议：健康 + 未闭环事件 + 高危漏洞 + AI 状态。"""
    from app.models.incident import Incident
    from app.models.security import Finding

    open_inc = db.query(Incident).filter(Incident.status.notin_(["closed", "resolved"])).count()
    high_findings = db.query(Finding).filter(Finding.severity.in_(["high", "critical"]),
                                             Finding.status == "open").count()
    cfg = get_llm_config(db)
    advice = []
    if high_findings:
        advice.append(f"存在 {high_findings} 个高危漏洞未修复，建议尽快修复并复测")
    if open_inc:
        advice.append(f"有 {open_inc} 个事件未闭环，建议逐条完成 AI 研判与人工审核")
    if cfg.provider == "mock":
        advice.append("未接入真实 AI 模型，研判能力有限——建议配置密钥获得深度分析")
    if not settings.wazuh_url:
        advice.append("未接入 Wazuh，无法自动收集主机告警——建议部署并配置（docs/deployment.md）")
    if not advice:
        advice.append("系统状态良好：无高危漏洞、无未闭环事件。建议保持日志审查与定期巡检")
    return ToolResult(True, "安全防护建议：" + "；".join(advice), {"advice": advice})


def _tool_help(db: Session, args: dict) -> ToolResult:
    return ToolResult(True, "我可以帮你完成：漏洞扫描、漏洞/事件查询、日志审查、报告生成、威胁情报查询、系统健康检查与安全防护建议。直接说指令即可，例如：“扫描 http://demo.local”“审查今天的日志”“应急响应”", {})


TOOLS: dict[str, tuple[str, object]] = {
    "scan": ("发起漏洞扫描", _tool_scan),
    "analyze_incident": ("AI 研判事件", _tool_analyze_incident),
    "findings": ("查询漏洞", _tool_findings),
    "incidents": ("查询安全事件 / 应急响应", _tool_incidents),
    "audit": ("日志审查", _tool_audit),
    "reports": ("查询安全报告", _tool_reports),
    "generate_report": ("生成安全报告", _tool_generate_report),
    "iocs": ("查询威胁情报", _tool_iocs),
    "health": ("系统健康检查", _tool_health),
    "security_advice": ("安全防护建议", _tool_advice),
    "help": ("能力介绍", _tool_help),
}

# mock 意图规则（LLM 不可用/失败时的兜底）。
# 顺序即优先级：更具体的意图（报告/扫描）排在宽泛意图（事件/健康）之前。
_INTENT_RULES = [
    (r"扫描|nuclei|扫一下", "scan"),
    (r"报告|撰写|写报告", "generate_report"),
    (r"日志|审查|审计", "audit"),
    (r"漏洞|findings", "findings"),
    (r"情报|ioc", "iocs"),
    (r"应急|响应|告警|事件|incident", "incidents"),
    (r"健康|状态|检查|正常吗", "health"),
    (r"防护|建议|加固|保障|安全吗|安全服务", "security_advice"),
]


class CopilotService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMClient(get_llm_config(db))

    # ------------------------------------------------------------------
    def handle(self, message: str, history: list[dict] | None = None) -> dict:
        """Full copilot turn: intent → tool → reply."""
        message = (message or "").strip()
        if not message:
            return {"reply": "请下达指令，例如：扫描 http://demo.local", "tool": "help"}

        # 1. intent
        tool_name, args, reasoning = self._resolve_intent(message)

        # 2. execute tool
        fn = TOOLS[tool_name][1]
        result = fn(self.db, args)  # type: ignore[operator]
        log_audit(self.db, "copilot.tool", "system", None,
                  detail={"tool": tool_name, "message": message[:100]})
        self.db.commit()

        # 3. reply (LLM when real model; templates in mock mode)
        reply = self._generate_reply(message, tool_name, result, history)
        return {
            "reply": reply,
            "tool": tool_name,
            "tool_label": TOOLS[tool_name][0],
            "result_ok": result.ok,
            "data": result.data,
        }

    # ------------------------------------------------------------------
    def _resolve_intent(self, message: str) -> tuple[str, dict, str]:
        # LLM intent resolution first (real model), rule fallback otherwise
        if self.llm.config.transport != "mock":
            try:
                raw = self.llm.complete_json(INTENT_SYSTEM_PROMPT, message)
                tool = str(raw.get("tool", "")).strip()
                args = raw.get("args") if isinstance(raw.get("args"), dict) else {}
                if tool in TOOLS:
                    return tool, args, str(raw.get("reasoning", ""))
            except (LLMError, json.JSONDecodeError, KeyError):
                logger.warning("copilot LLM intent failed, using rules")
        return self._rule_intent(message)

    def _rule_intent(self, message: str) -> tuple[str, dict, str]:
        low = message.lower()
        for pattern, tool in _INTENT_RULES:
            if re.search(pattern, low):
                # 报告类：提到具体事件 ID 才生成报告，否则列出已有报告
                if tool == "generate_report" and not re.search(r"[0-9a-f]{16,32}", message):
                    tool = "reports"
                return tool, self._extract_args(tool, message), "规则匹配"
        return "help", {}, "意图不明，转帮助"

    @staticmethod
    def _extract_args(tool: str, message: str) -> dict:
        if tool == "scan":
            # targets: 仅提取 ASCII 的 URL / IP / CIDR（排除中文指令词）
            targets = re.findall(
                r"(?:https?://)?[a-zA-Z0-9][a-zA-Z0-9.-]*\.(?:com|net|org|io|cn|local|xyz|top|dev)(?:[:/][^\s,，；]*)?"
                r"|\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?"
                r"|https?://[^\s,，；]+",
                message,
            )
            seen, out = set(), []
            for t in targets:
                if t not in seen:
                    seen.add(t)
                    out.append(t)
            return {"targets": out[:5]}
        if tool == "findings":
            sev = next((s for s in ("critical", "high", "medium", "low") if s in message.lower()), None)
            return {"severity": sev} if sev else {}
        if tool == "incidents":
            return {"open_only": True}
        if tool == "generate_report":
            m = re.search(r"[0-9a-f]{16,32}", message)
            return {"incident_id": m.group(0)} if m else {}
        return {}

    # ------------------------------------------------------------------
    def _generate_reply(self, message: str, tool: str, result: ToolResult,
                        history: list[dict] | None) -> str:
        if not result.ok:
            return result.summary
        if self.llm.config.transport != "mock":
            try:
                payload = json.dumps({"user": message, "tool": tool,
                                      "tool_result": result.summary,
                                      "data": result.data}, ensure_ascii=False, default=str)
                return self.llm.complete(REPLY_SYSTEM_PROMPT, payload, json_mode=False).strip()
            except LLMError:
                logger.warning("copilot LLM reply failed, using template")
        return self._template_reply(tool, result)

    @staticmethod
    def _template_reply(tool: str, result: ToolResult) -> str:
        if tool == "scan":
            return f"✅ {result.summary}。扫描由后台执行，完成后会自动在「漏洞管理」生成漏洞记录，并尝试关联安全事件。稍后可在页面查看进度。"
        if tool == "audit":
            return f"🔍 {result.summary}。如需导出完整日志，可在「日志审查」页操作。"
        if tool == "incidents":
            return f"🚨 {result.summary}。建议在「事件响应」中逐条点击 AI 研判，完成风险评分与人工审核。"
        if tool == "generate_report":
            return f"📄 {result.summary}。可在「安全报告」页下载 PDF。"
        if tool == "security_advice":
            return f"🛡️ {result.summary}。可让我继续执行具体操作，例如“修复漏洞优先级排序”“生成巡检报告”。"
        if tool == "health":
            return f"🩺 {result.summary}。"
        if tool == "help":
            return result.summary
        return f"{result.summary}。"
