"""API router aggregation (spec §51)."""
from fastapi import APIRouter

from app.api import analysis, assets, audit, auth, events, findings, health, incidents, iocs, maintenance, projects, reports, scans, settings
from integrations.wazuh.webhook import router as wazuh_webhook

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(assets.router)
api_router.include_router(events.router)
api_router.include_router(findings.router)
api_router.include_router(iocs.router)
api_router.include_router(incidents.router)
api_router.include_router(scans.router)
api_router.include_router(analysis.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(maintenance.router)
api_router.include_router(wazuh_webhook)
