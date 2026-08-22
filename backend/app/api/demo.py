"""Demo data source (安服·演示数据).

One click loads a realistic security dataset so the platform is immediately
usable for demos / training even before Wazuh & MISP are deployed:
  - 8 Wazuh-style alerts (brute force, command execution, webshell, ...)
  - 3 malicious IOCs (MISP style)
  - 2 assets
  - correlation engine auto-builds Incidents with evidence chains

Every artifact is clearly tagged as demo data (audit trail included).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.organization import User
from app.models.project import Project
from app.services.audit import log_audit
from app.services.correlation import CorrelationEngine

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_ASSETS = [
    {"name": "web-01", "ip": "10.10.10.10", "hostname": "web-01",
     "asset_type": "webapp", "environment": "production", "criticality": 5,
     "domain": "shop.example.com"},
    {"name": "db-01", "ip": "10.10.10.11", "hostname": "db-01",
     "asset_type": "database", "environment": "production", "criticality": 5},
]

DEMO_IOCS = [
    {"type": "ip", "value": "203.0.113.66", "confidence": 0.95, "tags": ["apt", "c2", "demo"]},
    {"type": "ip", "value": "198.51.100.23", "confidence": 0.85, "tags": ["scanner", "demo"]},
    {"type": "domain", "value": "evil-c2.example.net", "confidence": 0.9, "tags": ["c2", "demo"]},
]

DEMO_EVENTS = [
    {"event_type": "SSH brute force", "src_ip": "203.0.113.66", "dst_ip": "10.10.10.10",
     "severity": "high", "confidence": 0.9, "techniques": ["T1110"], "user": "root"},
    {"event_type": "Command execution detected", "src_ip": "203.0.113.66", "dst_ip": "10.10.10.10",
     "severity": "critical", "confidence": 0.95, "techniques": ["T1059.001"], "user": "www-data"},
    {"event_type": "Webshell upload detected", "src_ip": "198.51.100.23", "dst_ip": "10.10.10.10",
     "severity": "critical", "confidence": 0.9, "techniques": ["T1505.003"]},
    {"event_type": "Port scan detected", "src_ip": "198.51.100.23", "dst_ip": "10.10.10.10",
     "severity": "medium", "confidence": 0.6, "techniques": ["T1046"]},
    {"event_type": "Malicious outbound connection", "src_ip": "10.10.10.10", "dst_ip": "203.0.113.66",
     "severity": "high", "confidence": 0.85, "techniques": ["T1071"]},
    {"event_type": "Privilege escalation attempt", "src_ip": "203.0.113.66", "dst_ip": "10.10.10.10",
     "severity": "high", "confidence": 0.8, "techniques": ["T1068"]},
]


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> dict:
    """Load the demo dataset (assets + IOCs + alerts → correlated incidents)."""
    from app.models.project import Asset
    from app.models.security import IOC, SecurityEvent

    project = db.query(Project).first()
    if not project:
        project = Project(name="演示项目", description="SecFlow 演示数据")
        db.add(project)
        db.flush()

    asset_ids: dict[str, str] = {}
    for a in DEMO_ASSETS:
        asset = Asset(project_id=project.id, **a, tags=["demo"], status="active")
        db.add(asset)
        db.flush()
        asset_ids[a["name"]] = asset.id

    for ioc in DEMO_IOCS:
        ioc["source"] = "misp-demo"
        db.add(IOC(**ioc))
    db.flush()

    engine = CorrelationEngine(db)
    incidents = []
    for ev in DEMO_EVENTS:
        asset_id = asset_ids.get("web-01" if ev["dst_ip"] == "10.10.10.10" else "db-01")
        event = SecurityEvent(source="wazuh-demo", project_id=project.id,
                              asset_id=asset_id, **ev, indicators=[ev["src_ip"]], raw_data={"demo": True})
        db.add(event)
        db.flush()
        inc = engine.on_event(event)
        if inc:
            incidents.append(inc.id)
    db.commit()

    log_audit(db, "demo.seed", "system", None,
              detail={"assets": len(DEMO_ASSETS), "iocs": len(DEMO_IOCS),
                      "events": len(DEMO_EVENTS), "incidents": len(incidents)},
              username=user.username, user_id=user.id)
    db.commit()
    return {
        "status": "ok",
        "message": "演示数据已加载（标注 demo，可在「系统维护 → 数据管理」随时清空）",
        "loaded": {"assets": len(DEMO_ASSETS), "iocs": len(DEMO_IOCS),
                   "events": len(DEMO_EVENTS), "incidents": len(incidents)},
    }
