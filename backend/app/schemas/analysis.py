"""Operational schemas: scans, analysis, risk, reports, audit."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# --- Scans ---
class ScanCreate(BaseModel):
    project_id: str
    scan_type: str = "nuclei"
    targets: list[str] = Field(min_length=1)
    options: dict[str, Any] = {}


class ScanOut(ORMModel):
    id: str
    project_id: str | None = None
    scan_type: str
    targets: list = []
    options: dict = {}
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result_summary: dict = {}
    error: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None


# --- Analysis ---
class AnalyzeRequest(BaseModel):
    agents: list[str] | None = None  # default: all available
    force: bool = False


class AIAnalysisOut(ORMModel):
    id: str
    incident_id: str | None = None
    agent_type: str
    input: dict = {}
    output: dict = {}
    status: str
    model: str | None = None
    prompt_version: str | None = None
    error: str | None = None
    created_at: datetime | None = None


class RiskAssessmentOut(ORMModel):
    id: str
    incident_id: str | None = None
    finding_id: str | None = None
    risk_score: float
    risk_level: str
    factors: dict = {}
    created_at: datetime | None = None


# --- Reports ---
class ReportCreate(BaseModel):
    project_id: str | None = None
    incident_id: str | None = None
    report_type: str = "incident"
    title: str | None = None


class ReportOut(ORMModel):
    id: str
    project_id: str | None = None
    incident_id: str | None = None
    report_type: str
    title: str
    status: str
    content_pdf_path: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None


# --- Audit ---
class AuditLogOut(ORMModel):
    id: str
    user_id: str | None = None
    username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    detail: dict = {}
    ip: str | None = None
    timestamp: datetime | None = None
