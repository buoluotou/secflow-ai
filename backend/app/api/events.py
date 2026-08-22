"""Security events API (spec §51) + manual event ingestion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.organization import User
from app.models.security import SecurityEvent
from app.schemas.security import SecurityEventIn, SecurityEventOut
from app.services.audit import log_audit
from app.services.correlation import CorrelationEngine

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[SecurityEventOut])
def list_events(
    project_id: str | None = None,
    severity: str | None = None,
    src_ip: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(SecurityEvent)
    if project_id:
        query = query.filter(SecurityEvent.project_id == project_id)
    if severity:
        query = query.filter(SecurityEvent.severity == severity)
    if src_ip:
        query = query.filter(SecurityEvent.src_ip == src_ip)
    return query.order_by(SecurityEvent.timestamp.desc()).limit(min(limit, 500)).all()


@router.post("", response_model=SecurityEventOut, status_code=201)
def create_event(body: SecurityEventIn, db: Session = Depends(get_db),
                 user: User = Depends(require_write)):
    event = SecurityEvent(**body.model_dump())
    db.add(event)
    db.flush()
    incident = CorrelationEngine(db).on_event(event)
    log_audit(db, "event.create", "security_event", event.id,
              username=user.username, user_id=user.id,
              detail={"incident": incident.id if incident else None})
    db.commit()
    return event


@router.get("/{event_id}", response_model=SecurityEventOut)
def get_event(event_id: str, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    event = db.get(SecurityEvent, event_id)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    return event
