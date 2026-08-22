"""Audit logging service (spec §50)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.analysis import AuditLog


def log_audit(
    db: Session,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    user_id: str | None = None,
    username: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
        user_id=user_id,
        username=username,
        ip=ip,
    )
    db.add(entry)
    db.flush()
    return entry
