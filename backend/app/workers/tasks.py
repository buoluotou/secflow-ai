"""Async tasks (spec §52) — never block HTTP:

  - run_nuclei_scan     : nuclei scan job → Findings
  - sync_wazuh_events   : pull Wazuh alerts → SecurityEvents + correlation
  - enrich_misp_iocs    : query MISP for known IOCs → IOC store
  - analyze_incident    : full AI pipeline (triage/threat/vuln/risk)
  - generate_report     : incident / vulnerability report generation
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

# Register the SecFlow celery app as the process-wide default so that
# `@shared_task` proxies resolve to OUR broker (redis), not the bare
# default celery app (amqp://localhost:5672). Importing this module from
# anywhere (API route, worker CLI) triggers the registration.
from app.workers.celery_app import celery_app  # noqa: F401

from app.core.database import session_scope
from app.core.logging import get_logger
from app.models.analysis import ScanJob
from app.models.security import SecurityEvent
from app.services.analysis import AnalysisService
from app.services.correlation import CorrelationEngine
from app.services.reports import ReportService

logger = get_logger("secflow.worker", service="secflow-worker")


# ---------------------------------------------------------------------------
@shared_task(bind=True, name="app.workers.tasks.run_nuclei_scan")
def run_nuclei_scan(self, scan_job_id: str) -> dict:
    from integrations.nuclei.mapper import upsert_finding
    from integrations.nuclei.models import NucleiResult
    from integrations.nuclei.parser import parse_line
    from integrations.nuclei.runner import run

    with session_scope() as db:
        job = db.get(ScanJob, scan_job_id)
        if not job:
            return {"error": "scan job not found"}
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.flush()

        try:
            raw_results = run(job.targets, job.options)
            findings_created = 0
            incidents: list[str] = []
            for raw in raw_results:
                result = parse_line(raw) if isinstance(raw, str) else NucleiResult.model_validate(raw)
                if not result or not result.info.severity:
                    continue
                values = {
                    "project_id": job.project_id,
                    "source": "nuclei",
                    "template_id": result.template_id,
                    "title": result.info.name or result.template_id,
                    "description": result.info.description,
                    "severity": result.info.severity,
                    "cvss": result.cvss,
                    "cwe": result.cwe,
                    "request": (result.request or "")[:8000] or None,
                    "response": (result.response or "")[:8000] or None,
                    "evidence": result.matcher_status and (
                        result.extracted_results[0] if result.extracted_results else result.matched_at
                    ),
                    "remediation": result.info.remediation,
                    "status": "open",
                    "external_id": f"{result.template_id}:{result.host or result.matched_at}",
                }
                finding = upsert_finding(db, values)
                findings_created += 1
                incident = CorrelationEngine(db).on_finding(finding)
                if incident:
                    incidents.append(incident.id)

            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            job.result_summary = {
                "raw_results": len(raw_results),
                "findings_created": findings_created,
                "incidents": incidents,
            }
            logger.info("scan %s done: %s findings", scan_job_id, findings_created)
            return job.result_summary
        except Exception as exc:  # noqa: BLE001
            # Persist the failure BEFORE the session_scope rollback would
            # discard it — the exception still propagates to Celery so the
            # task is recorded as failed.
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.error = str(exc)[:2000]
            db.commit()
            logger.error("scan %s failed: %s", scan_job_id, exc)
            raise


# ---------------------------------------------------------------------------
@shared_task(name="app.workers.tasks.sync_wazuh_events")
def sync_wazuh_events() -> dict:
    from integrations.wazuh.client import WazuhClient
    from integrations.wazuh.mapper import map_to_event, upsert_event
    from integrations.wazuh.parser import parse_alert

    with session_scope() as db:
        since = datetime.now(timezone.utc) - timedelta(
            seconds=db_first_lookback(db)
        )
        client = WazuhClient()
        alerts = client.get_alerts(since=since)
        created = 0
        incidents: list[str] = []
        for alert in alerts:
            parsed = parse_alert(alert)
            values = map_to_event(parsed)
            event = upsert_event(db, values)
            if not values.get("external_id") or event.id not in existing_ids(db):
                created += 1
            incident = CorrelationEngine(db).on_event(event)
            if incident:
                incidents.append(incident.id)
        logger.info("wazuh sync: %s alerts, %s incidents", len(alerts), len(incidents))
        return {"alerts": len(alerts), "incidents": incidents}


def existing_ids(db) -> set[str]:
    """All stored SecurityEvent ids — computed ONCE per sync (avoids an
    O(n) query inside the per-alert loop)."""
    from app.models.security import SecurityEvent

    return {e.id for e in db.query(SecurityEvent.id).all()}


def db_first_lookback(db) -> int:
    from app.core.config import settings

    last = db.query(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).first()
    if last:
        return 60  # incremental sync: last 60s window overlap
    return settings.wazuh_sync_initial_lookback


# ---------------------------------------------------------------------------
@shared_task(name="app.workers.tasks.enrich_misp_iocs")
def enrich_misp_iocs() -> dict:
    from app.models.security import IOC
    from integrations.misp.client import MISPClient
    from integrations.misp.mapper import upsert_ioc
    from integrations.misp.parser import event_to_iocs

    with session_scope() as db:
        client = MISPClient()
        known = {i.value for i in db.query(IOC).limit(2000).all()}
        imported = 0
        # Enrich from a window of recent MISP events
        try:
            events = client.list_recent_events(limit=50)
        except Exception as exc:  # noqa: BLE001
            logger.warning("misp enrich failed: %s", exc)
            return {"error": str(exc)}
        for ev in events:
            for ioc_dict in event_to_iocs(ev):
                if ioc_dict["value"] in values:
                    continue
                upsert_ioc(db, ioc_dict)
                imported += 1
        logger.info("misp enrich: %s new iocs", imported)
        return {"imported": imported}


# ---------------------------------------------------------------------------
@shared_task(name="app.workers.tasks.analyze_incident")
def analyze_incident(incident_id: str, agents: list[str] | None = None) -> dict:
    from app.models.incident import Incident

    with session_scope() as db:
        incident = db.get(Incident, incident_id)
        if not incident:
            return {"error": "incident not found"}
        service = AnalysisService(db)
        results = service.analyze_incident(incident, agents=agents)
        return {k: (v or {}) for k, v in results.items()}


# ---------------------------------------------------------------------------
@shared_task(name="app.workers.tasks.generate_report")
def generate_report(incident_id: str, created_by: str | None = None) -> dict:
    from app.models.incident import Incident

    with session_scope() as db:
        incident = db.get(Incident, incident_id)
        if not incident:
            return {"error": "incident not found"}
        report = ReportService(db).generate_incident_report(incident, created_by=created_by)
        return {"report_id": report.id, "status": report.status}
