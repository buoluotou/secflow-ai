"""AI output schemas — every agent output must validate against these
Pydantic models (spec §35: "必须 JSON Schema 校验")."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TriageOutput(BaseModel):
    classification: str = Field(description="true_positive | false_positive | likely_true_positive | likely_false_positive")
    severity: str = Field(description="info | low | medium | high | critical")
    confidence: float = Field(ge=0.0, le=1.0)
    attack_stage: str | None = None
    mitre_techniques: list[str] = []
    evidence_ids: list[str] = []
    reasoning_summary: str = ""
    recommendations: list[str] = []


class ThreatOutput(BaseModel):
    malicious: bool
    confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str] = []
    related_entities: list[str] = []
    evidence_ids: list[str] = []


class VulnerabilityOutput(BaseModel):
    authenticity: str = Field(description="confirmed | unconfirmed | false_positive")
    remediation_priority: str = Field(description="low | medium | high | critical")
    impact_scope: list[str] = []
    exploit_risk: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str] = []
    reasoning_summary: str = ""


class ReportOutput(BaseModel):
    summary: str = ""
    timeline_narrative: str = ""
    recommendations: list[str] = []
    evidence_ids: list[str] = []


OUTPUT_MODELS = {
    "triage": TriageOutput,
    "threat": ThreatOutput,
    "vuln": VulnerabilityOutput,
    "report": ReportOutput,
}
