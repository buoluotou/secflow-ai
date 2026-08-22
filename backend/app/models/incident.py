"""Incident and AttackTechnique models (spec §27)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import PkMixin, TimestampMixin


class Incident(Base, PkMixin, TimestampMixin):
    __tablename__ = "incidents"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    attack_stage: Mapped[str | None] = mapped_column(String(50), index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_to: Mapped[str | None] = mapped_column(String(255))

    # Linked entity ids (events/findings/iocs) that triggered this incident
    related_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    related_finding_ids: Mapped[list] = mapped_column(JSON, default=list)
    related_ioc_ids: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    correlation_reason: Mapped[str | None] = mapped_column(String(2000))

    # Human review (spec §40)
    ai_decision: Mapped[str | None] = mapped_column(String(30))
    human_decision: Mapped[str | None] = mapped_column(String(30))  # approve | reject | modify
    reviewer: Mapped[str | None] = mapped_column(String(255))
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    techniques: Mapped[list["AttackTechnique"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class AttackTechnique(Base, PkMixin, TimestampMixin):
    __tablename__ = "attack_techniques"

    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    technique_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # T1059.001
    name: Mapped[str | None] = mapped_column(String(255))
    tactic: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(2000))
    source: Mapped[str] = mapped_column(String(50), default="ai")

    incident: Mapped[Incident | None] = relationship(back_populates="techniques")
