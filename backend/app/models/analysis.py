"""Operational models: AIAnalysis, RiskAssessment, Report, ScanJob, AuditLog,
SystemSetting (runtime configuration KV)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import PkMixin, TimestampMixin


class SystemSetting(Base, PkMixin, TimestampMixin):
    """Runtime key-value configuration (e.g. LLM provider settings set from
    the web UI — takes effect immediately without restarting services)."""
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class AIAnalysis(Base, PkMixin, TimestampMixin):
    __tablename__ = "ai_analyses"

    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    agent_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)  # triage|threat|vuln|report
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    model: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    error: Mapped[str | None] = mapped_column(String(2000))


class RiskAssessment(Base, PkMixin, TimestampMixin):
    __tablename__ = "risk_assessments"

    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[str | None] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", index=True)
    factors: Mapped[dict] = mapped_column(JSON, default=dict)


class Report(Base, PkMixin, TimestampMixin):
    __tablename__ = "reports"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), index=True
    )
    report_type: Mapped[str] = mapped_column(String(30), default="incident", index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_md: Mapped[str | None] = mapped_column(Text)
    content_pdf_path: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_by: Mapped[str | None] = mapped_column(String(255))


class ScanJob(Base, PkMixin, TimestampMixin):
    __tablename__ = "scan_jobs"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    scan_type: Mapped[str] = mapped_column(String(30), default="nuclei")
    targets: Mapped[list] = mapped_column(JSON, default=list)
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000))
    created_by: Mapped[str | None] = mapped_column(String(255))


class AuditLog(Base, PkMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    username: Mapped[str | None] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
