"""Security domain models: SecurityEvent, Finding, IOC, Evidence (spec §23–§26)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import PkMixin, TimestampMixin, utcnow


class SecurityEvent(Base, PkMixin, TimestampMixin):
    __tablename__ = "security_events"

    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # wazuh | manual | webhook
    event_type: Mapped[str | None] = mapped_column(String(200), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utcnow)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    user: Mapped[str | None] = mapped_column(String(255))
    src_ip: Mapped[str | None] = mapped_column(String(64), index=True)
    src_port: Mapped[int | None] = mapped_column(Integer)
    dst_ip: Mapped[str | None] = mapped_column(String(64), index=True)
    dst_port: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    indicators: Mapped[list] = mapped_column(JSON, default=list)
    techniques: Mapped[list] = mapped_column(JSON, default=list)  # ATT&CK ids
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # external dedup key (e.g. wazuh alert id)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)


class Finding(Base, PkMixin, TimestampMixin):
    __tablename__ = "findings"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # nuclei | manual
    template_id: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    cvss: Mapped[float | None] = mapped_column(Float)
    cwe: Mapped[str | None] = mapped_column(String(50))
    request: Mapped[str | None] = mapped_column(String(8000))
    response: Mapped[str | None] = mapped_column(String(8000))
    evidence: Mapped[str | None] = mapped_column(String(4000))
    remediation: Mapped[str | None] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # external dedup key (e.g. nuclei template + matched host)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)


class IOC(Base, PkMixin, TimestampMixin):
    __tablename__ = "iocs"

    type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # ip|domain|url|hash|email
    value: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="misp", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # external dedup key (e.g. misp attribute uuid)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)


class Evidence(Base, PkMixin, TimestampMixin):
    __tablename__ = "evidence"

    type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(String(8000))
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
