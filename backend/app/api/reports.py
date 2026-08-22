"""Reports API (spec §51)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.analysis import Report
from app.models.incident import Incident
from app.models.organization import User
from app.schemas.analysis import ReportCreate, ReportOut
from app.services.audit import log_audit
from app.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(
    project_id: str | None = None,
    report_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Report)
    if project_id:
        query = query.filter(Report.project_id == project_id)
    if report_type:
        query = query.filter(Report.report_type == report_type)
    return query.order_by(Report.created_at.desc()).limit(100).all()


@router.post("", response_model=ReportOut, status_code=201)
def create_report(body: ReportCreate, db: Session = Depends(get_db),
                  user: User = Depends(require_write)):
    if body.incident_id:
        incident = db.get(Incident, body.incident_id)
        if not incident:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
        report = ReportService(db).generate_incident_report(incident, created_by=user.username)
    else:
        report = ReportService(db).generate_vulnerability_report(
            body.project_id, created_by=user.username
        )
    db.commit()
    return report


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


@router.get("/{report_id}/markdown")
def report_markdown(report_id: str, db: Session = Depends(get_db),
                    _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return {"report_id": report.id, "content": report.content_md or ""}


@router.get("/{report_id}/pdf")
def report_pdf(report_id: str, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report or not report.content_pdf_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF not available")
    return FileResponse(
        report.content_pdf_path,
        media_type="application/pdf",
        filename=f"{report.id}.pdf",
    )
