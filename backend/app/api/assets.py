"""Assets API (spec §22, §51)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.core.database import get_db
from app.models.organization import User
from app.models.project import Asset
from app.schemas.project import AssetCreate, AssetOut, AssetUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
def list_assets(
    project_id: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Asset)
    if project_id:
        query = query.filter(Asset.project_id == project_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Asset.name.ilike(like))
            | (Asset.ip.ilike(like))
            | (Asset.hostname.ilike(like))
            | (Asset.domain.ilike(like))
        )
    return query.order_by(Asset.created_at.desc()).all()


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(body: AssetCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_write)):
    asset = Asset(**body.model_dump())
    db.add(asset)
    db.flush()
    log_audit(db, "asset.create", "asset", asset.id,
              username=user.username, user_id=user.id)
    db.commit()
    return asset


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, body: AssetUpdate, db: Session = Depends(get_db),
                 user: User = Depends(require_write)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(asset, k, v)
    log_audit(db, "asset.update", "asset", asset.id,
              username=user.username, user_id=user.id)
    db.commit()
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_write)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    db.delete(asset)
    log_audit(db, "asset.delete", "asset", asset_id,
              username=user.username, user_id=user.id)
    db.commit()
