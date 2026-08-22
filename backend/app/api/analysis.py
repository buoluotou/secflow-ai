"""Analysis API — AI analysis records + risk assessments (spec §51)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.analysis import AIAnalysis, RiskAssessment
from app.models.organization import User
from app.schemas.analysis import AIAnalysisOut, RiskAssessmentOut

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("", response_model=list[AIAnalysisOut])
def list_analysis(
    incident_id: str | None = None,
    agent_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(AIAnalysis)
    if incident_id:
        query = query.filter(AIAnalysis.incident_id == incident_id)
    if agent_type:
        query = query.filter(AIAnalysis.agent_type == agent_type)
    return query.order_by(AIAnalysis.created_at.desc()).limit(200).all()


@router.get("/{analysis_id}", response_model=AIAnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    analysis = db.get(AIAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return analysis


@router.get("/incident/{incident_id}/risk", response_model=list[RiskAssessmentOut])
def incident_risk(incident_id: str, db: Session = Depends(get_db),
                  _: User = Depends(get_current_user)):
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.incident_id == incident_id)
        .order_by(RiskAssessment.created_at.desc())
        .all()
    )
