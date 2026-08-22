"""Wazuh mapper — normalized alert dict → SecurityEvent model fields."""
from __future__ import annotations

from typing import Any

from app.models.security import SecurityEvent

SOURCE = "wazuh"


def map_to_event(parsed: dict[str, Any], project_id: str | None = None,
                 asset_id: str | None = None) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "event_type": parsed.get("event_type"),
        "timestamp": parsed.get("timestamp"),
        "project_id": project_id,
        "asset_id": asset_id,
        "user": parsed.get("user"),
        "src_ip": parsed.get("src_ip"),
        "src_port": parsed.get("src_port"),
        "dst_ip": parsed.get("dst_ip"),
        "dst_port": parsed.get("dst_port"),
        "severity": parsed.get("severity", "medium"),
        "confidence": parsed.get("confidence", 0.5),
        "indicators": parsed.get("indicators", []),
        "techniques": parsed.get("techniques", []),
        "raw_data": parsed.get("raw_data", {}),
        "external_id": parsed.get("external_id"),
    }


def upsert_event(db, values: dict[str, Any]) -> SecurityEvent:
    """Insert a SecurityEvent, deduplicating on (source, external_id)."""
    external_id = values.get("external_id")
    if external_id:
        existing = (
            db.query(SecurityEvent)
            .filter(SecurityEvent.source == SOURCE, SecurityEvent.external_id == external_id)
            .first()
        )
        if existing:
            return existing
    event = SecurityEvent(**values)
    db.add(event)
    db.flush()
    return event
