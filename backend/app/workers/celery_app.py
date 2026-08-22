"""Celery application (spec §18, §52) — async tasks share the same models."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "secflow",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=200,
    beat_schedule={
        "sync-wazuh-events": {
            "task": "app.workers.tasks.sync_wazuh_events",
            "schedule": settings.wazuh_sync_interval_seconds,
        },
        "enrich-misp-iocs": {
            "task": "app.workers.tasks.enrich_misp_iocs",
            "schedule": settings.misp_enrich_interval_seconds,
        },
    },
)
