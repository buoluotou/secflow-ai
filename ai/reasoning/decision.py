"""Decision reasoning (spec §5, §40) — high-risk actions require human approval.

V1 enforces: AI recommends → human approves/rejects/modifies. This module is
the state machine + permission checks. No dangerous action is ever executed
by the AI directly.
"""
from __future__ import annotations

from typing import Any

VALID_DECISIONS = ("approve", "reject", "modify")

# States after human review
APPROVED = "approved"
REJECTED = "rejected"
MODIFIED = "awaiting_review"


def is_high_risk(action: str) -> bool:
    """Actions that must never auto-execute."""
    return action in {
        "block_src_ip",
        "quarantine_asset",
        "disable_account",
        "delete_ioc",
        "execute_remediation",
        "send_block_notification",
    }


def evaluate_decision(ai_decision: str, recommendations: list[str]) -> dict[str, Any]:
    """Prepare a human review request from an AI analysis.

    Returns:
      {"requires_human": True, "high_risk_actions": [...], "review": {...}}
    """
    high_risk = [r for r in recommendations if is_high_risk(r)]
    return {
        "requires_human": bool(high_risk) or ai_decision not in ("accept_low", "close"),
        "high_risk_actions": high_risk,
        "review": {
            "ai_decision": ai_decision,
            "recommendations": recommendations,
        },
    }


def apply_review(
    incident: Any,
    decision: str,
    comment: str | None = None,
    modifications: dict[str, Any] | None = None,
    reviewer: str | None = None,
) -> dict[str, Any]:
    """Apply a human review decision to an incident object (SQLAlchemy model)."""
    if decision not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision: {decision} (use {VALID_DECISIONS})")

    from datetime import datetime, timezone

    incident.human_decision = decision
    incident.reviewer = reviewer
    incident.review_comment = comment
    incident.reviewed_at = datetime.now(timezone.utc)

    if decision == "approve":
        incident.status = APPROVED
    elif decision == "reject":
        incident.status = REJECTED
    elif decision == "modify":
        incident.status = MODIFIED
        if modifications:
            for key, value in modifications.items():
                if hasattr(incident, key) and key not in ("id", "project_id"):
                    setattr(incident, key, value)
    return {
        "incident_id": incident.id,
        "decision": decision,
        "status": incident.status,
        "reviewer": reviewer,
    }
