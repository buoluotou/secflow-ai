"""Wazuh webhook receiver (spec §28) — FastAPI router.

Wazuh can forward alerts to an integration (custom Webhook) — this router
ingests them, parses, maps, stores and runs correlation.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.security import SecurityEvent
from app.services.audit import log_audit
from app.services.correlation import CorrelationEngine
from integrations.wazuh.mapper import map_to_event, upsert_event
from integrations.wazuh.parser import parse_alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/wazuh", tags=["webhooks"])


@router.post("")
@router.post("/")
async def receive_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    body = await request.json()
    alerts = body.get("alerts") if isinstance(body, dict) and "alerts" in body else [body]
    created: list[str] = []
    incidents: list[str] = []
    for alert in alerts:
        parsed = parse_alert(alert)
        values = map_to_event(parsed)
        event = upsert_event(db, values)
        created.append(event.id)
        incident = CorrelationEngine(db).on_event(event)
        if incident:
            incidents.append(incident.id)
    db.commit()
    log_audit(db, "webhook.wazuh.received", "security_event", None,
              detail={"events": len(created), "incidents": incidents})
    db.commit()
    return {"received": len(created), "events": created, "incidents": incidents}
