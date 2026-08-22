"""Findings API (spec §51)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.organization import User
from app.models.security import Finding
from app.schemas.security import FindingIn, FindingOut
from app.services.audit import log_audit

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=list[FindingOut])
def list_findings(
    project_id: str | None = None,
    severity: str | None = None,
    status_: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Finding)
    if project_id:
        query = query.filter(Finding.project_id == project_id)
    if severity:
        query = query.filter(Finding.severity == severity)
    if status_:
        query = query.filter(Finding.status == status_)
    return query.order_by(Finding.last_seen.desc()).limit(min(limit, 500)).all()


@router.post("", response_model=FindingOut, status_code=201)
def create_finding(body: FindingIn, db: Session = Depends(get_db),
                   user: User = Depends(require_write)):
    finding = Finding(**body.model_dump())
    db.add(finding)
    db.flush()
    log_audit(db, "finding.create", "finding", finding.id,
              username=user.username, user_id=user.id)
    db.commit()
    return finding


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: str, db: Session = Depends(get_db),
                _: User = Depends(get_current_user)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")
    return finding


@router.patch("/{finding_id}", response_model=FindingOut)
def update_finding(finding_id: str, body: dict, db: Session = Depends(get_db),
                   user: User = Depends(require_write)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")
    allowed = {"status", "severity", "remediation", "title", "description"}
    for k, v in body.items():
        if k in allowed:
            setattr(finding, k, v)
    log_audit(db, "finding.update", "finding", finding.id,
              username=user.username, user_id=user.id)
    db.commit()
    return finding
