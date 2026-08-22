"""Test bootstrap — repo-root imports (ai/integrations/risk/reports) and
an in-memory SQLite database."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = REPO_ROOT / "backend"
for p in (REPO_ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

os.environ.setdefault("DATABASE_URL_OVERRIDE", "sqlite:///./test_secflow.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef-0123456789abcdef")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECFLOW_ADMIN_USER", "testadmin")
os.environ.setdefault("SECFLOW_ADMIN_PASSWORD", "TestPass12345")
os.environ.setdefault("REPORT_DIR", str(Path(BACKEND) / "test_reports"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    # fresh DB file per session
    db_path = Path(BACKEND) / "test_secflow.db"
    db_path.unlink(missing_ok=True)
    get_settings.cache_clear()
    from app.core.database import init_db

    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
    db_path.unlink(missing_ok=True)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "TestPass12345"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def project_id(client, admin_token) -> str:
    resp = client.post(
        "/api/projects",
        json={"name": "测试项目", "description": "pytest"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]
