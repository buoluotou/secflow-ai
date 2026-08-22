"""Nuclei mapper — NucleiResult → Finding model fields (spec §29)."""
from __future__ import annotations

from typing import Any

from app.models.security import Finding
from integrations.nuclei.models import NucleiResult

SOURCE = "nuclei"


def map_to_finding(result: NucleiResult, project_id: str | None = None,
                   asset_id: str | None = None) -> dict[str, Any]:
    host = result.host or result.matched_at
    return {
        "project_id": project_id,
        "asset_id": asset_id,
        "source": SOURCE,
        "template_id": result.template_id,
        "title": result.info.name or result.template_id,
        "description": result.info.description,
        "severity": result.info.severity,
        "cvss": result.cvss,
        "cwe": result.cwe,
        "request": result.request[:8000] if result.request else None,
        "response": result.response[:8000] if result.response else None,
        "evidence": result.matcher_status and (result.extracted_results[0] if result.extracted_results else result.matched_at),
        "remediation": result.info.remediation,
        "status": "open",
        "external_id": f"{result.template_id}:{host}",
    }


def upsert_finding(db, values: dict[str, Any]) -> Finding:
    """Insert a Finding, deduplicating on (source, external_id)."""
    external_id = values.get("external_id")
    if external_id:
        existing = (
            db.query(Finding)
            .filter(Finding.source == SOURCE, Finding.external_id == external_id)
            .first()
        )
        if existing:
            existing.last_seen = values.get("last_seen") or existing.last_seen
            if existing.status == "open" and values.get("status") == "open":
                pass
            return existing
    finding = Finding(**values)
    db.add(finding)
    db.flush()
    return finding
