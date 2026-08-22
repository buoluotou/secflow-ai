"""Maintenance API — system upkeep from the web UI (安服·系统维护).

  GET  /api/maintenance/stats       — data volume per table
  POST /api/maintenance/reset-data  — wipe all business data (keep users)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.organization import User
from app.services.audit import log_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

BUSINESS_TABLES = [
    "risk_assessments", "ai_analyses", "reports", "scan_jobs", "audit_logs",
    "attack_techniques", "incidents", "evidence", "iocs", "findings",
    "security_events", "assets", "projects",
]


@router.get("/stats")
def maintenance_stats(db: Session = Depends(get_db),
                      _: User = Depends(require_admin)) -> dict:
    counts = {}
    for t in BUSINESS_TABLES + ["users"]:
        try:
            counts[t] = db.execute(text(f'SELECT count(*) FROM "{t}"')).scalar()
        except Exception:  # noqa: BLE001
            counts[t] = 0
    return {"tables": counts}


@router.post("/reset-data")
def reset_data(db: Session = Depends(get_db),
               user: User = Depends(require_admin)) -> dict:
    """Wipe ALL business data (incidents, events, findings, scans, reports,
    audit logs, ...) but keep user accounts and AI runtime settings."""
    try:
        # DELETE is portable across PostgreSQL and SQLite (ids are UUIDs,
        # no sequences to reset). FK constraints are handled by the delete
        # order (children first) — PostgreSQL relies on CASCADE deletes.
        for t in BUSINESS_TABLES:
            db.execute(text(f'DELETE FROM "{t}"'))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f"清空数据失败: {exc}") from exc
    log_audit(db, "maintenance.reset_data", "system", None,
              username=user.username, user_id=user.id)
    db.commit()
    return {"status": "ok", "message": "全部业务数据已清空（用户与 AI 配置保留）"}
