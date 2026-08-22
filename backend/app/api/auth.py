"""Auth API (spec §51): POST /api/auth/login; bootstrap admin creation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserOut
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        log_audit(db, "auth.login_failed", "user", None,
                  detail={"username": body.username}, username=body.username,
                  ip=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User disabled")
    log_audit(db, "auth.login", "user", user.id, username=user.username,
              ip=request.client.host if request.client else None)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.flush()
    log_audit(db, "user.create", "user", user.id, username=user.username)
    db.commit()
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/bootstrap-admin", response_model=TokenResponse)
def bootstrap_admin(body: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    """Create the first admin — only works while no admin exists (first boot)."""
    admin_exists = db.query(User).filter(User.role == "admin").first()
    if admin_exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Admin already exists")
    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role="admin",
    )
    db.add(user)
    db.flush()
    log_audit(db, "user.bootstrap_admin", "user", user.id, username=user.username)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role))
