"""MISP parser — MISP event dict → normalized IOC dicts."""
from __future__ import annotations

from typing import Any

from integrations.misp.models import MISPEvent

# MISP attribute type → SecFlow IOC type
TYPE_MAP = {
    "ip-src": "ip",
    "ip-dst": "ip",
    "ip": "ip",
    "domain": "domain",
    "hostname": "domain",
    "url": "url",
    "link": "url",
    "md5": "hash",
    "sha1": "hash",
    "sha256": "hash",
    "sha512": "hash",
    "ssdeep": "hash",
    "email": "email",
    "email-src": "email",
    "email-dst": "email",
}


def parse_event(event: dict[str, Any]) -> MISPEvent:
    return MISPEvent.model_validate(event)


def event_to_iocs(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract SecFlow IOC dicts from a raw MISP event response item."""
    ev = parse_event(event)
    tags = [t.get("name", "") for t in ev.tags if isinstance(t, dict)]
    iocs: list[dict[str, Any]] = []
    for attr in ev.Attribute:
        ioc_type = TYPE_MAP.get(attr.type)
        if not ioc_type or not attr.value:
            continue
        iocs.append(
            {
                "type": ioc_type,
                "value": attr.value,
                "source": "misp",
                "confidence": 0.8 if attr.to_ids else 0.5,
                "tags": [*tags, attr.category or "misp"],
                "external_id": attr.uuid or attr.id,
                "event_info": ev.info,
                "event_id": ev.id,
            }
        )
    return iocs
