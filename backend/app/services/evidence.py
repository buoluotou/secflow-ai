"""Evidence Engine (spec §26, §32) — every AI conclusion must bind evidence.

Each evidence row is content-addressed by a SHA-256 of its canonical payload,
so re-importing the same raw data never duplicates evidence.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.security import Evidence


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def compute_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


class EvidenceEngine:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        type_: str,
        source: str,
        title: str,
        content: str | None = None,
        raw_data: dict[str, Any] | None = None,
        source_id: str | None = None,
        timestamp=None,
    ) -> Evidence:
        payload = {
            "type": type_,
            "source": source,
            "source_id": source_id,
            "title": title,
            "content": content,
            "raw_data": raw_data or {},
            "timestamp": str(timestamp) if timestamp else None,
        }
        digest = compute_hash(payload)
        existing = self.db.query(Evidence).filter(Evidence.hash == digest).first()
        if existing:
            return existing
        evidence = Evidence(
            type=type_,
            source=source,
            source_id=source_id,
            title=title,
            content=content,
            raw_data=raw_data or {},
            timestamp=timestamp,
            hash=digest,
        )
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def from_security_event(self, event) -> Evidence:
        return self.add(
            type_="wazuh_alert" if event.source == "wazuh" else "log",
            source=event.source,
            source_id=event.external_id or event.id,
            title=f"{event.event_type or 'security event'} from {event.src_ip or 'unknown'}",
            content=(event.raw_data or {}).get("summary") or event.event_type,
            raw_data=event.raw_data or {},
            timestamp=event.timestamp,
        )

    def from_finding(self, finding) -> Evidence:
        return self.add(
            type_="nuclei_finding" if finding.source == "nuclei" else "finding",
            source=finding.source,
            source_id=finding.external_id or finding.id,
            title=finding.title,
            content=finding.evidence or finding.description,
            raw_data={
                "template_id": finding.template_id,
                "severity": finding.severity,
                "cvss": finding.cvss,
                "cwe": finding.cwe,
                "request": finding.request,
                "response": finding.response,
            },
            timestamp=finding.last_seen,
        )

    def from_ioc(self, ioc) -> Evidence:
        return self.add(
            type_="misp_ioc" if ioc.source == "misp" else "ioc",
            source=ioc.source,
            source_id=ioc.external_id or ioc.id,
            title=f"IOC {ioc.type}: {ioc.value}",
            content=f"Indicator of type {ioc.type} flagged with confidence {ioc.confidence}",
            raw_data={"type": ioc.type, "value": ioc.value, "tags": ioc.tags},
            timestamp=ioc.last_seen,
        )

    def from_historical_event(self, event) -> Evidence:
        return self.add(
            type_="historical_event",
            source=event.source,
            source_id=event.external_id or event.id,
            title=f"Historical event: {event.event_type or event.src_ip or 'n/a'}",
            content=(event.raw_data or {}).get("summary") or event.event_type,
            raw_data=event.raw_data or {},
            timestamp=event.timestamp,
        )
