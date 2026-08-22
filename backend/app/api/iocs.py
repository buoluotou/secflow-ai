"""IOC API (spec §51): list + search (with live MISP fallback)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.organization import User
from app.models.security import IOC
from app.schemas.security import IOCIn, IOCSearch, IOCOut
from app.services.audit import log_audit

router = APIRouter(prefix="/iocs", tags=["iocs"])


@router.get("", response_model=list[IOCOut])
def list_iocs(
    type_: str | None = None,
    q: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(IOC)
    if type_:
        query = query.filter(IOC.type == type_)
    if q:
        query = query.filter(IOC.value.ilike(f"%{q}%"))
    return query.order_by(IOC.last_seen.desc()).limit(min(limit, 500)).all()


@router.post("", response_model=IOCOut, status_code=201)
def create_ioc(body: IOCIn, db: Session = Depends(get_db),
               user: User = Depends(require_write)):
    ioc = IOC(**body.model_dump())
    db.add(ioc)
    db.flush()
    log_audit(db, "ioc.create", "ioc", ioc.id, username=user.username, user_id=user.id)
    db.commit()
    return ioc


@router.post("/search", response_model=list[IOCOut])
def search_iocs(body: IOCSearch, db: Session = Depends(get_db),
                _: User = Depends(get_current_user)):
    """Search local IOC store; optionally enriches from MISP when not found."""
    query = db.query(IOC).filter(IOC.value.ilike(f"%{body.value}%"))
    if body.type:
        query = query.filter(IOC.type == body.type)
    if body.source:
        query = query.filter(IOC.source == body.source)
    local = query.all()
    if not local and body.source != "misp":
        try:
            from integrations.misp.client import MISPClient
            from integrations.misp.mapper import upsert_ioc
            from integrations.misp.parser import event_to_iocs

            client = MISPClient()
            events = client.search_value(body.value)
            for ev in events:
                for ioc_dict in event_to_iocs(ev):
                    if ioc_dict["value"] == body.value:
                        ioc = upsert_ioc(db, ioc_dict)
                        local.append(ioc)
            db.commit()
        except Exception:  # noqa: BLE001  (MISP unavailable is fine)
            pass
    return local


@router.delete("/{ioc_id}", status_code=204)
def delete_ioc(ioc_id: str, db: Session = Depends(get_db),
               user: User = Depends(require_write)):
    ioc = db.get(IOC, ioc_id)
    if not ioc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "IOC not found")
    db.delete(ioc)
    log_audit(db, "ioc.delete", "ioc", ioc_id, username=user.username, user_id=user.id)
    db.commit()
