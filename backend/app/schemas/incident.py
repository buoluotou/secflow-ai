"""Incident and review schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class IncidentCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    severity: str = "medium"
    attack_stage: str | None = None
    related_event_ids: list[str] = []
    related_finding_ids: list[str] = []
    related_ioc_ids: list[str] = []
    evidence_ids: list[str] = []
    correlation_reason: str | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    severity: str | None = None
    confidence: float | None = None
    attack_stage: str | None = None
    assigned_to: str | None = None


class ReviewRequest(BaseModel):
    decision: str  # approve | reject | modify
    comment: str | None = None
    modifications: dict[str, Any] | None = None


class IncidentOut(ORMModel):
    id: str
    project_id: str
    title: str
    description: str | None = None
    status: str
    severity: str
    confidence: float
    attack_stage: str | None = None
    detected_at: datetime | None = None
    closed_at: datetime | None = None
    assigned_to: str | None = None
    related_event_ids: list = []
    related_finding_ids: list = []
    related_ioc_ids: list = []
    evidence_ids: list = []
    correlation_reason: str | None = None
    ai_decision: str | None = None
    human_decision: str | None = None
    reviewer: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None


class AttackTechniqueOut(ORMModel):
    id: str
    technique_id: str
    name: str | None = None
    tactic: str | None = None
    description: str | None = None
    source: str
