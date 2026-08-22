"""Auth schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str
    email: str | None = None
    full_name: str | None = None
    role: str
    organization_id: str | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str | None = None
    full_name: str | None = None
    password: str = Field(min_length=8, max_length=128)
    role: str = "analyst"
