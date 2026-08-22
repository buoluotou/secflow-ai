"""Scans API (spec §15, §51): create scan jobs → Celery workers."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.analysis import ScanJob
from app.models.organization import User
from app.schemas.analysis import ScanCreate, ScanOut
from app.services.audit import log_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanOut, status_code=202)
def create_scan(body: ScanCreate, db: Session = Depends(get_db),
                user: User = Depends(require_write)):
    job = ScanJob(
        project_id=body.project_id,
        scan_type=body.scan_type,
        targets=body.targets,
        options=body.options,
        status="queued",
        created_by=user.username,
    )
    db.add(job)
    db.flush()
    log_audit(db, "scan.create", "scan_job", job.id,
              username=user.username, user_id=user.id,
              detail={"targets": body.targets[:5]})
    db.commit()

    # enqueue (worker consumes via Redis; broker unavailable only logs)
    try:
        from app.workers.tasks import run_nuclei_scan

        run_nuclei_scan.delay(job.id)
    except Exception as exc:  # noqa: BLE001  (broker down — worker can pick up later)
        logger.warning("scan %s enqueue failed: %s", job.id, exc)
    return job


@router.get("", response_model=list[ScanOut])
def list_scans(project_id: str | None = None, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    query = db.query(ScanJob)
    if project_id:
        query = query.filter(ScanJob.project_id == project_id)
    return query.order_by(ScanJob.created_at.desc()).limit(100).all()


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str, db: Session = Depends(get_db),
             _: User = Depends(get_current_user)):
    job = db.get(ScanJob, scan_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return job
