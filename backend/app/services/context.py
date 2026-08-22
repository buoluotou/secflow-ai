"""Context Engine (spec §33) — assembles the unified context fed to AI agents."""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.analysis import AIAnalysis
from app.models.incident import Incident
from app.models.project import Asset, Project
from app.models.security import Evidence, Finding, IOC, SecurityEvent


class ContextEngine:
    def __init__(self, db: Session):
        self.db = db

    def for_incident(self, incident: Incident) -> dict:
        """Build the spec §33 context envelope for an incident."""
        current_events: list[SecurityEvent] = []
        for eid in incident.related_event_ids:
            ev = self.db.get(SecurityEvent, eid)
            if ev:
                current_events.append(ev)

        findings: list[Finding] = []
        for fid in incident.related_finding_ids:
            f = self.db.get(Finding, fid)
            if f:
                findings.append(f)

        iocs: list[IOC] = []
        for iid in incident.related_ioc_ids:
            i = self.db.get(IOC, iid)
            if i:
                iocs.append(i)

        evidence = [
            self.db.get(Evidence, eid) for eid in incident.evidence_ids
        ]
        evidence = [e for e in evidence if e is not None]

        assets: list[Asset] = []
        project = self.db.get(Project, incident.project_id)
        for ev in current_events:
            if ev.asset_id:
                asset = self.db.get(Asset, ev.asset_id)
                if asset and asset not in assets:
                    assets.append(asset)
        for f in findings:
            if f.asset_id:
                asset = self.db.get(Asset, f.asset_id)
                if asset and asset not in assets:
                    assets.append(asset)

        # Historical events on the same asset / src_ip (exclude current ones)
        history: list[SecurityEvent] = []
        asset_ids = [a.id for a in assets]
        src_ips = {ev.src_ip for ev in current_events if ev.src_ip}
        conditions = []
        if asset_ids:
            conditions.append(SecurityEvent.asset_id.in_(asset_ids))
        if src_ips:
            conditions.append(SecurityEvent.src_ip.in_(list(src_ips)))
        if conditions:
            q = self.db.query(SecurityEvent).filter(or_(*conditions))
            history = q.order_by(SecurityEvent.timestamp.desc()).limit(50).all()
        current_ids = {ev.id for ev in current_events}
        history = [h for h in history if h.id not in current_ids]

        attack_context = {
            "techniques": sorted({t for ev in current_events for t in (ev.techniques or [])}),
            "stage": incident.attack_stage,
        }

        return {
            "incident": {
                "id": incident.id,
                "title": incident.title,
                "status": incident.status,
                "severity": incident.severity,
                "detected_at": str(incident.detected_at),
            },
            "current_event": [self._event_dict(e) for e in current_events],
            "asset": [self._asset_dict(a) for a in assets],
            "history": [self._event_dict(e) for e in history[:20]],
            "findings": [self._finding_dict(f) for f in findings],
            "threat_intel": [self._ioc_dict(i) for i in iocs],
            "evidence": [
                {"id": e.id, "type": e.type, "source": e.source, "title": e.title} for e in evidence
            ],
            "attack_context": attack_context,
        }

    @staticmethod
    def _event_dict(e: SecurityEvent) -> dict:
        return {
            "id": e.id,
            "source": e.source,
            "event_type": e.event_type,
            "timestamp": str(e.timestamp),
            "user": e.user,
            "src_ip": e.src_ip,
            "src_port": e.src_port,
            "dst_ip": e.dst_ip,
            "dst_port": e.dst_port,
            "severity": e.severity,
            "confidence": e.confidence,
            "indicators": e.indicators,
            "techniques": e.techniques,
            "raw_data": e.raw_data,
        }

    @staticmethod
    def _asset_dict(a: Asset) -> dict:
        return {
            "id": a.id,
            "name": a.name,
            "hostname": a.hostname,
            "ip": a.ip,
            "domain": a.domain,
            "asset_type": a.asset_type,
            "environment": a.environment,
            "criticality": a.criticality,
            "owner": a.owner,
            "tags": a.tags,
            "status": a.status,
        }

    @staticmethod
    def _finding_dict(f: Finding) -> dict:
        return {
            "id": f.id,
            "template_id": f.template_id,
            "title": f.title,
            "severity": f.severity,
            "cvss": f.cvss,
            "cwe": f.cwe,
            "status": f.status,
            "first_seen": str(f.first_seen),
        }

    @staticmethod
    def _ioc_dict(i: IOC) -> dict:
        return {"id": i.id, "type": i.type, "value": i.value, "confidence": i.confidence, "tags": i.tags}
