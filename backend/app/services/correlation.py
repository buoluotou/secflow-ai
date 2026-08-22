"""Correlation Engine (spec §31) — the first truly original core module.

Correlates data across Wazuh events, Nuclei findings and MISP threat intel
on shared join keys (asset, src_ip, domain, user, IOC, timestamp) and
automatically creates Incidents with evidence links.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.analysis import AuditLog
from app.models.incident import Incident
from app.models.project import Asset, Project
from app.models.security import Evidence, Finding, IOC, SecurityEvent
from app.services.audit import log_audit
from app.services.evidence import EvidenceEngine

logger = logging.getLogger(__name__)

JOIN_KEYS = ("asset_id", "src_ip", "dst_ip", "domain", "user", "ioc")


class CorrelationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.evidence = EvidenceEngine(db)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    def on_event(self, event: SecurityEvent) -> Incident | None:
        """Called when a new security event arrives (webhook / sync)."""
        return self._correlate(trigger_event=event)

    def on_finding(self, finding: Finding) -> Incident | None:
        return self._correlate(trigger_finding=finding)

    def on_ioc(self, ioc: IOC) -> Incident | None:
        return self._correlate(trigger_ioc=ioc)

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    def _correlate(
        self,
        trigger_event: SecurityEvent | None = None,
        trigger_finding: Finding | None = None,
        trigger_ioc: IOC | None = None,
    ) -> Incident | None:
        evidence_ids: list[str] = []
        related_events: list[str] = []
        related_findings: list[str] = []
        related_iocs: list[str] = []
        reasons: list[str] = []
        techniques: set[str] = set()
        project_id: str | None = None

        # --- 1. Trigger evidence ---
        if trigger_event:
            ev = self.evidence.from_security_event(trigger_event)
            evidence_ids.append(ev.id)
            related_events.append(trigger_event.id)
            project_id = trigger_event.project_id or project_id
            techniques.update(trigger_event.techniques or [])
            reasons.append(f"Wazuh event '{trigger_event.event_type}' (sev={trigger_event.severity})")
            # MISP enrichment: src_ip / indicators are IOC?
            matched = self._match_iocs(
                values=[trigger_event.src_ip, *trigger_event.indicators],
            )
            for ioc, ioc_ev in matched:
                evidence_ids.append(ioc_ev.id)
                related_iocs.append(ioc.id)
                reasons.append(f"src_ip/indicator {ioc.value} is malicious IOC (conf={ioc.confidence})")

        if trigger_finding:
            ev = self.evidence.from_finding(trigger_finding)
            evidence_ids.append(ev.id)
            related_findings.append(trigger_finding.id)
            project_id = trigger_finding.project_id or project_id
            reasons.append(f"Nuclei finding '{trigger_finding.title}' (sev={trigger_finding.severity})")
            # same-asset historical events
            if trigger_finding.asset_id:
                history = (
                    self.db.query(SecurityEvent)
                    .filter(SecurityEvent.asset_id == trigger_finding.asset_id)
                    .order_by(SecurityEvent.timestamp.desc())
                    .limit(20)
                    .all()
                )
                for h in history:
                    hev = self.evidence.from_historical_event(h)
                    evidence_ids.append(hev.id)
                    related_events.append(h.id)
                if history:
                    reasons.append(
                        f"asset has {len(history)} historical security event(s)"
                    )
                    techniques.update({t for h in history for t in (h.techniques or [])})

        if trigger_ioc:
            ev = self.evidence.from_ioc(trigger_ioc)
            evidence_ids.append(ev.id)
            related_iocs.append(trigger_ioc.id)
            reasons.append(f"IOC {trigger_ioc.type}:{trigger_ioc.value} (conf={trigger_ioc.confidence})")
            # events from this IOC
            q = self.db.query(SecurityEvent)
            if trigger_ioc.type == "ip":
                q = q.filter(SecurityEvent.src_ip == trigger_ioc.value)
            elif trigger_ioc.type in ("domain", "url"):
                q = q.filter(
                    (SecurityEvent.src_ip == trigger_ioc.value)
                    | (SecurityEvent.indicators.contains(trigger_ioc.value))
                )
            else:
                q = q.filter(SecurityEvent.indicators.contains(trigger_ioc.value))
            for evt in q.limit(20).all():
                related_events.append(evt.id)
                e = self.evidence.from_security_event(evt)
                evidence_ids.append(e.id)
            if related_events:
                reasons.append(f"IOC seen in {len(related_events)} security event(s)")

        # --- 2. Cross-source matching on join keys (spec §31) ---
        if trigger_event and trigger_event.asset_id:
            findings = (
                self.db.query(Finding)
                .filter(Finding.asset_id == trigger_event.asset_id, Finding.status != "false_positive")
                .all()
            )
            for f in findings:
                related_findings.append(f.id)
                e = self.evidence.from_finding(f)
                evidence_ids.append(e.id)
                reasons.append(f"asset also has open finding '{f.title}'")
            # asset domain matching
            asset = self.db.get(Asset, trigger_event.asset_id) if trigger_event.asset_id else None
            if asset and (asset.domain or asset.ip):
                matched = self._match_iocs(values=[asset.domain, asset.ip])
                for ioc, ioc_ev in matched:
                    evidence_ids.append(ioc_ev.id)
                    related_iocs.append(ioc.id)
                    reasons.append(f"asset {asset.name} matches malicious IOC {ioc.value}")

        if trigger_finding and trigger_finding.asset_id:
            events = (
                self.db.query(SecurityEvent)
                .filter(SecurityEvent.asset_id == trigger_finding.asset_id)
                .all()
            )
            for evt in events:
                related_events.append(evt.id)
                e = self.evidence.from_security_event(evt)
                evidence_ids.append(e.id)
                reasons.append(f"asset with finding also has Wazuh event '{evt.event_type}'")

        # --- 3. Decide: is this correlation strong enough for an incident? ---
        if not self._is_incident(trigger_event, trigger_finding, trigger_ioc, reasons):
            return None

        project_id = project_id or self._default_project_id(trigger_event, trigger_finding, trigger_ioc)

        # --- 4. Dedupe / merge into existing open incident ---
        src_ips = {trigger_event.src_ip} if trigger_event and trigger_event.src_ip else set()
        existing = self._find_open_incident(
            project_id, related_events, related_findings, related_iocs, src_ips
        )
        severity = self._estimate_severity(
            trigger_event=trigger_event,
            trigger_finding=trigger_finding,
            trigger_ioc=trigger_ioc,
        )

        if existing:
            existing.evidence_ids = sorted(set(existing.evidence_ids + evidence_ids))
            existing.related_event_ids = sorted(set(existing.related_event_ids + related_events))
            existing.related_finding_ids = sorted(
                set(existing.related_finding_ids + related_findings)
            )
            existing.related_ioc_ids = sorted(set(existing.related_ioc_ids + related_iocs))
            if severity and severity != existing.severity:
                existing.severity = severity
            if reasons:
                existing.correlation_reason = " | ".join(dict.fromkeys(existing.correlation_reason.split(" | ") + reasons))[:2000]
            self.db.flush()
            log_audit(self.db, "correlation.merge", "incident", existing.id,
                      detail={"added_evidence": len(evidence_ids)})
            return existing

        title = self._build_title(trigger_event, trigger_finding, trigger_ioc)
        incident = Incident(
            project_id=project_id,
            title=title,
            description="\n".join(f"- {r}" for r in reasons),
            status="new",
            severity=severity,
            confidence=0.6,
            attack_stage=self._estimate_attack_stage(trigger_event, techniques),
            related_event_ids=sorted(set(related_events)),
            related_finding_ids=sorted(set(related_findings)),
            related_ioc_ids=sorted(set(related_iocs)),
            evidence_ids=sorted(set(evidence_ids)),
            correlation_reason=" | ".join(dict.fromkeys(reasons))[:2000],
        )
        self.db.add(incident)
        self.db.flush()
        for t in techniques:
            from app.models.incident import AttackTechnique

            self.db.add(
                AttackTechnique(
                    incident_id=incident.id, technique_id=t, source="correlation"
                )
            )
        log_audit(self.db, "correlation.incident_created", "incident", incident.id,
                  detail={"reasons": reasons[:10]})
        logger.info("correlation created incident %s", incident.id)
        return incident

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _match_iocs(self, values: list[str | None]) -> list[tuple[IOC, Evidence]]:
        """Match ALL IOC records for the given values (multiple sources may
        flag the same indicator)."""
        out: list[tuple[IOC, Evidence]] = []
        for v in values:
            if not v:
                continue
            for ioc in self.db.query(IOC).filter(IOC.value == v).all():
                out.append((ioc, self.evidence.from_ioc(ioc)))
        return out

    def _is_incident(
        self,
        trigger_event: SecurityEvent | None,
        trigger_finding: Finding | None,
        trigger_ioc: IOC | None,
        reasons: list[str],
    ) -> bool:
        if trigger_ioc and trigger_event is None and trigger_finding is None:
            # IOC alone is intel, not an incident — unless it touches events
            return bool(reasons) and any("security event" in r for r in reasons)
        if trigger_event:
            sev = trigger_event.severity or "low"
            if sev in ("high", "critical"):
                return True
            if trigger_event.confidence and trigger_event.confidence >= 0.8:
                return True
        if trigger_finding:
            sev = trigger_finding.severity or "low"
            if sev in ("high", "critical"):
                return True
            if trigger_finding.cvss and trigger_finding.cvss >= 7.0:
                return True
        # multiple evidence strands
        return len(reasons) >= 2

    def _find_open_incident(
        self,
        project_id: str | None,
        events: list[str],
        findings: list[str],
        iocs: list[str],
        src_ips: set[str] | None = None,
    ) -> Incident | None:
        open_statuses = ("new", "triaging", "investigating", "awaiting_review", "approved")
        q = self.db.query(Incident).filter(Incident.status.in_(open_statuses))
        if project_id:
            q = q.filter(Incident.project_id == project_id)
        for inc in q.all():
            if set(events) & set(inc.related_event_ids or []):
                return inc
            if set(findings) & set(inc.related_finding_ids or []):
                return inc
            if set(iocs) & set(inc.related_ioc_ids or []):
                return inc
            # join key: same attacker src_ip across different events (spec §31)
            if src_ips:
                overlap = (
                    self.db.query(SecurityEvent.id)
                    .filter(
                        SecurityEvent.id.in_(inc.related_event_ids or []),
                        SecurityEvent.src_ip.in_(list(src_ips)),
                    )
                    .first()
                )
                if overlap:
                    return inc
        return None

    def _default_project_id(
        self,
        trigger_event: SecurityEvent | None,
        trigger_finding: Finding | None,
        trigger_ioc: IOC | None,
    ) -> str | None:
        pid = None
        for obj in (trigger_event, trigger_finding):
            if obj and getattr(obj, "project_id", None):
                pid = obj.project_id
        if pid:
            return pid
        first = self.db.query(Project).first()
        return first.id if first else None

    def _estimate_severity(
        self,
        trigger_event: SecurityEvent | None,
        trigger_finding: Finding | None,
        trigger_ioc: IOC | None,
    ) -> str:
        ranks = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        best = "low"
        for obj, attr in ((trigger_event, "severity"), (trigger_finding, "severity")):
            if obj:
                sev = str(getattr(obj, attr, "low") or "low")
                if ranks.get(sev, 0) > ranks[best]:
                    best = sev
        if trigger_ioc and trigger_ioc.confidence and trigger_ioc.confidence >= 0.7:
            if ranks[best] < 2:
                best = "medium"
        return best

    def _estimate_attack_stage(
        self, trigger_event: SecurityEvent | None, techniques: set[str]
    ) -> str | None:
        if not techniques:
            if trigger_event and trigger_event.event_type:
                et = trigger_event.event_type.lower()
                for stage in ("execution", "initial_access", "persistence", "command_and_control"):
                    if stage in et:
                        return stage
            return None
        return "execution"  # refined by AI triage later

    @staticmethod
    def _build_title(
        trigger_event: SecurityEvent | None,
        trigger_finding: Finding | None,
        trigger_ioc: IOC | None,
    ) -> str:
        if trigger_event:
            return f"[{trigger_event.severity.upper()}] {trigger_event.event_type or 'Security event'} correlated"
        if trigger_finding:
            return f"[{trigger_finding.severity.upper()}] {trigger_finding.title} correlated"
        if trigger_ioc:
            return f"[IOC] Malicious indicator {trigger_ioc.type}:{trigger_ioc.value}"
        return "Correlated security incident"
