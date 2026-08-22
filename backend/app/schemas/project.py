"""Project & Asset schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    organization_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectOut(ORMModel):
    id: str
    name: str
    description: str | None = None
    status: str
    organization_id: str | None = None
    created_at: object | None = None


class AssetCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=200)
    hostname: str | None = None
    ip: str | None = None
    domain: str | None = None
    asset_type: str = "server"
    environment: str = "production"
    criticality: int = Field(default=1, ge=1, le=5)
    owner: str | None = None
    tags: list[str] = []
    status: str = "active"


class AssetUpdate(BaseModel):
    name: str | None = None
    hostname: str | None = None
    ip: str | None = None
    domain: str | None = None
    asset_type: str | None = None
    environment: str | None = None
    criticality: int | None = Field(default=None, ge=1, le=5)
    owner: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class AssetOut(ORMModel):
    id: str
    project_id: str
    name: str
    hostname: str | None = None
    ip: str | None = None
    domain: str | None = None
    asset_type: str
    environment: str
    criticality: int
    owner: str | None = None
    tags: list = []
    status: str
    created_at: object | None = None
