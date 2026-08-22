"""Domain constants shared across models, schemas and services."""
from __future__ import annotations

# --- Users ---
ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"

# --- Assets ---
ASSET_TYPES = ("server", "workstation", "network", "webapp", "database", "cloud", "iot", "other")
ASSET_ENVIRONMENTS = ("production", "staging", "development", "test", "dmz", "internal")
ASSET_STATUSES = ("active", "inactive", "maintenance", "retired")

# --- Security events ---
EVENT_SOURCES = ("wazuh", "manual", "webhook")

# --- Findings ---
FINDING_SOURCES = ("nuclei", "manual", "import")
FINDING_STATUSES = ("open", "confirmed", "false_positive", "remediated", "accepted_risk", "closed")

# --- IOC types ---
IOC_TYPES = ("ip", "domain", "url", "hash", "email")

# --- Evidence ---
EVIDENCE_TYPES = ("wazuh_alert", "nuclei_finding", "misp_ioc", "historical_event", "asset_info", "manual", "log")
EVIDENCE_SOURCES = ("wazuh", "nuclei", "misp", "asset", "history", "manual")

# --- Incidents ---
INCIDENT_STATUSES = (
    "new",
    "triaging",
    "investigating",
    "awaiting_review",
    "approved",
    "rejected",
    "contained",
    "resolved",
    "closed",
)
INCIDENT_SEVERITIES = ("info", "low", "medium", "high", "critical")

# --- AI analyses ---
AGENT_TYPES = ("triage", "threat", "vuln", "report")
ANALYSIS_STATUSES = ("pending", "running", "completed", "failed")

# --- Risk ---
RISK_LEVELS = ("low", "medium", "high", "critical")

# --- Reports ---
REPORT_TYPES = ("incident", "vulnerability", "inspection")
REPORT_STATUSES = ("draft", "generated", "reviewed", "final")

# --- Scans ---
SCAN_TYPES = ("nuclei", "nuclei_single", "custom")
SCAN_STATUSES = ("queued", "running", "completed", "failed", "cancelled")

# --- ATT&CK ---
ATTACK_STAGES = (
    "reconnaissance",
    "initial_access",
    "execution",
    "persistence",
    "privilege_escalation",
    "defense_evasion",
    "credential_access",
    "discovery",
    "lateral_movement",
    "collection",
    "command_and_control",
    "exfiltration",
    "impact",
)
