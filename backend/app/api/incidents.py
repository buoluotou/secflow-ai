"""Incidents API (spec §51): CRUD + analyze + approve/reject."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.incident import Incident
from app.models.organization import User
from app.schemas.analysis import AnalyzeRequest
from app.schemas.incident import (
    IncidentCreate,
    IncidentOut,
    IncidentUpdate,
    ReviewRequest,
)
from app.services.analysis import AnalysisService
from app.services.audit import log_audit
from ai.reasoning.decision import apply_review

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    project_id: str | None = None,
    status_: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Incident)
    if project_id:
        query = query.filter(Incident.project_id == project_id)
    if status_:
        query = query.filter(Incident.status == status_)
    if severity:
        query = query.filter(Incident.severity == severity)
    return query.order_by(Incident.detected_at.desc()).limit(min(limit, 500)).all()


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(body: IncidentCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_write)):
    incident = Incident(**body.model_dump())
    db.add(incident)
    db.flush()
    log_audit(db, "incident.create", "incident", incident.id,
              username=user.username, user_id=user.id)
    db.commit()
    return incident


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    return incident


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(incident_id: str, body: IncidentUpdate,
                    db: Session = Depends(get_db), user: User = Depends(require_write)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(incident, k, v)
    log_audit(db, "incident.update", "incident", incident.id,
              username=user.username, user_id=user.id)
    db.commit()
    return incident


@router.post("/{incident_id}/analyze")
def analyze_incident(
    incident_id: str,
    body: AnalyzeRequest | None = None,
    async_mode: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_write),
):
    """Run the AI pipeline (triage/threat/vuln/report + risk).

    Synchronous by default (returns results inline). Pass `?async_mode=true`
    to enqueue on Celery and return immediately (202-style response).
    `force=true` re-runs agents even when a completed analysis exists.
    """
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")

    agents = body.agents if body else None
    force = bool(body and body.force)

    if async_mode:
        try:
            from app.workers.tasks import analyze_incident as analyze_task

            analyze_task.delay(incident_id, agents=agents)
            log_audit(db, "ai.analyze_queued", "incident", incident.id,
                      username=user.username, user_id=user.id)
            db.commit()
            return {"status": "queued", "incident_id": incident_id}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                f"任务队列不可用: {exc}") from exc

    try:
        results = AnalysisService(db).analyze_incident(incident, agents=agents, force=force)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("analysis failed for incident %s", incident_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f"AI 研判失败: {exc}") from exc
    return {
        "incident_id": incident_id,
        "status": "completed",
        "force": force,
        "results": results,
    }


@router.post("/{incident_id}/approve")
def approve_incident(incident_id: str, body: ReviewRequest | None = None,
                     db: Session = Depends(get_db), user: User = Depends(require_write)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    result = apply_review(incident, "approve", comment=(body.comment if body else None),
                          reviewer=user.username)
    log_audit(db, "incident.approve", "incident", incident.id,
              username=user.username, user_id=user.id, detail=result)
    db.commit()
    return result


@router.post("/{incident_id}/reject")
def reject_incident(incident_id: str, body: ReviewRequest | None = None,
                    db: Session = Depends(get_db), user: User = Depends(require_write)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    result = apply_review(incident, "reject", comment=(body.comment if body else None),
                          reviewer=user.username)
    log_audit(db, "incident.reject", "incident", incident.id,
              username=user.username, user_id=user.id, detail=result)
    db.commit()
    return result
