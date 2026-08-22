"""Seed data — first admin + optional demo dataset (Demo 01)."""
from __future__ import annotations

import logging
import os

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.organization import User

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USER = os.getenv("SECFLOW_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.getenv("SECFLOW_ADMIN_PASSWORD", "Admin@123456")


def seed_admin() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "admin").first():
            db.add(
                User(
                    username=DEFAULT_ADMIN_USER,
                    full_name="SecFlow Admin",
                    hashed_password=hash_password(DEFAULT_ADMIN_PASS),
                    role="admin",
                )
            )
            db.commit()
            logger.info("seeded admin user %r (change the default password!)", DEFAULT_ADMIN_USER)
    finally:
        db.close()


def seed_demo_data() -> None:
    """Demo 01 dataset: a project, assets, one malicious IOC and a demo
    web-application asset ready for Nuclei scanning."""
    from app.models.project import Asset, Project
    from app.models.security import IOC

    db = SessionLocal()
    try:
        if db.query(Project).first():
            return
        project = Project(
            name="Demo 01 — Web 入侵事件自动研判",
            description="自建靶场演示：Nuclei 扫描 → Wazuh 告警 → MISP IOC → 关联 → AI 研判 → 报告",
            status="active",
        )
        db.add(project)
        db.flush()

        db.add_all(
            [
                Asset(
                    project_id=project.id,
                    name="demo-web",
                    hostname="demo-web",
                    ip="172.20.0.10",
                    domain="demo.local",
                    asset_type="webapp",
                    environment="dmz",
                    criticality=4,
                    owner="secflow",
                    tags=["demo", "web"],
                    status="active",
                ),
                Asset(
                    project_id=project.id,
                    name="demo-db",
                    hostname="demo-db",
                    ip="172.20.0.11",
                    asset_type="database",
                    environment="internal",
                    criticality=5,
                    owner="secflow",
                    tags=["demo", "db"],
                    status="active",
                ),
            ]
        )
        db.add(
            IOC(
                type="ip",
                value="203.0.113.66",
                source="demo",
                confidence=0.9,
                tags=["demo", "malicious"],
            )
        )
        db.commit()
        logger.info("seeded demo data for project %s", project.id)
    finally:
        db.close()
