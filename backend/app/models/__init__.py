"""Model registry — import all models so metadata is complete."""
from app.models.analysis import AIAnalysis, AuditLog, Report, RiskAssessment, ScanJob, SystemSetting
from app.models.incident import AttackTechnique, Incident
from app.models.organization import Organization, User
from app.models.project import Asset, Project
from app.models.security import Evidence, Finding, IOC, SecurityEvent

__all__ = [
    "AIAnalysis",
    "Asset",
    "AttackTechnique",
    "AuditLog",
    "Evidence",
    "Finding",
    "IOC",
    "Incident",
    "Organization",
    "Project",
    "Report",
    "RiskAssessment",
    "ScanJob",
    "SecurityEvent",
    "SystemSetting",
    "User",
]
