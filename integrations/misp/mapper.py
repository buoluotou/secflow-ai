"""MISP mapper — normalized IOC dict → IOC model fields."""
from __future__ import annotations

from typing import Any

from app.models.security import IOC

SOURCE = "misp"


def map_to_ioc(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": parsed["type"],
        "value": parsed["value"],
        "source": SOURCE,
        "confidence": parsed.get("confidence", 0.5),
        "tags": parsed.get("tags", []),
        "external_id": parsed.get("external_id"),
    }


def upsert_ioc(db, values: dict[str, Any]) -> IOC:
    """Insert an IOC, deduplicating on (source, type, value)."""
    existing = (
        db.query(IOC)
        .filter(IOC.source == SOURCE, IOC.type == values["type"], IOC.value == values["value"])
        .first()
    )
    if existing:
        existing.confidence = max(existing.confidence, values.get("confidence", 0.5))
        existing.tags = sorted(set(existing.tags or []) | set(values.get("tags", [])))
        return existing
    ioc = IOC(**values)
    db.add(ioc)
    db.flush()
    return ioc
