"""Report service — orchestrates Report Engine (spec §38)."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import AIAnalysis, Report, RiskAssessment
from app.models.incident import Incident
from app.models.project import Project
from app.services.audit import log_audit
from app.services.context import ContextEngine
from reports.engine import build_incident_report, render_pdf

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def generate_incident_report(self, incident: Incident, created_by: str | None = None) -> Report:
        ctx = ContextEngine(self.db).for_incident(incident)
        analyses = (
            self.db.query(AIAnalysis)
            .filter(AIAnalysis.incident_id == incident.id)
            .order_by(AIAnalysis.created_at.desc())
            .all()
        )
        triage = next((a for a in analyses if a.agent_type == "triage"), None)
        report_agent = next((a for a in analyses if a.agent_type == "report"), None)
        risk = (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.incident_id == incident.id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )

        ai_analysis = triage.output if triage else None
        # merge report-agent narrative into the AI section
        if report_agent and report_agent.output:
            ai_analysis = {**(ai_analysis or {}), **report_agent.output}
        human_review = {
            "ai_decision": incident.ai_decision,
            "human_decision": incident.human_decision,
            "reviewer": incident.reviewer,
            "review_comment": incident.review_comment,
        } if incident.human_decision else None

        title = f"安全事件报告 — {incident.title}"
        md = build_incident_report(
            context=ctx,
            ai_analysis=ai_analysis,
            risk={"risk_score": risk.risk_score, "risk_level": risk.risk_level,
                  "factors": risk.factors} if risk else None,
            human_review=human_review,
            incident={
                "id": incident.id,
                "title": incident.title,
                "status": incident.status,
                "severity": incident.severity,
                "confidence": incident.confidence,
                "attack_stage": incident.attack_stage,
                "detected_at": str(incident.detected_at),
                "description": incident.description,
            },
        )

        report_dir = Path(settings.report_dir) / "generated"
        pdf_path = report_dir / f"incident_{incident.id}.pdf"
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
            render_pdf(md, pdf_path, title=title)
            pdf_rel = str(pdf_path)
        except Exception as exc:  # noqa: BLE001  (PDF is best-effort)
            logger.warning("PDF render failed: %s", exc)
            pdf_rel = None

        report = Report(
            project_id=incident.project_id,
            incident_id=incident.id,
            report_type="incident",
            title=title,
            content_md=md,
            content_pdf_path=pdf_rel,
            status="generated",
            created_by=created_by,
        )
        self.db.add(report)
        self.db.flush()
        log_audit(self.db, "report.generate", "report", report.id,
                  detail={"incident_id": incident.id, "pdf": bool(pdf_rel)})
        return report

    def generate_vulnerability_report(self, project_id: str, created_by: str | None = None) -> Report:
        project = self.db.get(Project, project_id)
        title = f"漏洞扫描报告 — {project.name if project else project_id}"
        md = self._vuln_markdown(project_id)
        report = Report(
            project_id=project_id,
            report_type="vulnerability",
            title=title,
            content_md=md,
            status="generated",
            created_by=created_by,
        )
        self.db.add(report)
        self.db.flush()
        log_audit(self.db, "report.generate", "report", report.id,
                  detail={"project_id": project_id, "type": "vulnerability"})
        return report

    @staticmethod
    def _vuln_markdown(project_id: str) -> str:
        return (
            f"# 漏洞扫描报告\n\n> 项目 ID：`{project_id}` | 生成时间：{_now()}\n\n"
            "## 1. 漏洞汇总\n\n本报告由 SecFlow AI 基于 Nuclei 扫描结果自动汇总，"
            "详见前端 Findings 页面。\n\n## 2. 处置建议\n\n- 按严重性从高到低修复；\n"
            "- 高危漏洞需在 7 天内完成整改；\n- 修复后重新扫描验证。\n"
        )


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
