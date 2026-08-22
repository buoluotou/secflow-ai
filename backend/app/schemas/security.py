"""Security domain schemas: SecurityEvent, Finding, IOC, Evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# --- SecurityEvent ---
class SecurityEventIn(BaseModel):
    source: str = "manual"
    event_type: str | None = None
    timestamp: datetime | None = None
    project_id: str | None = None
    asset_id: str | None = None
    user: str | None = None
    src_ip: str | None = None
    src_port: int | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    severity: str = "medium"
    confidence: float = 0.5
    indicators: list[str] = []
    techniques: list[str] = []
    raw_data: dict[str, Any] = {}
    external_id: str | None = None


class SecurityEventOut(ORMModel):
    id: str
    source: str
    event_type: str | None = None
    timestamp: datetime | None = None
    project_id: str | None = None
    asset_id: str | None = None
    user: str | None = None
    src_ip: str | None = None
    src_port: int | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    severity: str
    confidence: float
    indicators: list = []
    techniques: list = []
    external_id: str | None = None


# --- Finding ---
class FindingIn(BaseModel):
    project_id: str | None = None
    asset_id: str | None = None
    source: str = "nuclei"
    template_id: str | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    severity: str = "medium"
    cvss: float | None = None
    cwe: str | None = None
    request: str | None = None
    response: str | None = None
    evidence: str | None = None
    remediation: str | None = None
    status: str = "open"
    external_id: str | None = None


class FindingOut(ORMModel):
    id: str
    project_id: str | None = None
    asset_id: str | None = None
    source: str
    template_id: str | None = None
    title: str
    description: str | None = None
    severity: str
    cvss: float | None = None
    cwe: str | None = None
    request: str | None = None
    response: str | None = None
    evidence: str | None = None
    remediation: str | None = None
    status: str
    first_seen: datetime | None = None
    last_seen: datetime | None = None


# --- IOC ---
class IOCIn(BaseModel):
    type: str
    value: str
    source: str = "misp"
    confidence: float = 0.5
    tags: list[str] = []
    external_id: str | None = None


class IOCSearch(BaseModel):
    type: str | None = None
    value: str
    source: str | None = None


class IOCOut(ORMModel):
    id: str
    type: str
    value: str
    source: str
    confidence: float
    tags: list = []
    first_seen: datetime | None = None
    last_seen: datetime | None = None


# --- Evidence ---
class EvidenceOut(ORMModel):
    id: str
    type: str
    source: str
    source_id: str | None = None
    title: str
    content: str | None = None
    raw_data: dict = {}
    timestamp: datetime | None = None
    hash: str
