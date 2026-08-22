"""Monorepo path bootstrap.

Ensures the repo-root packages (``ai``, ``integrations``, ``risk``,
``reports``) are importable when running from this directory, e.g.:

    cd backend
    uvicorn app.main:app --reload
    celery -A app.workers.celery_app worker

Python imports this module automatically at interpreter startup when the
current working directory is on ``sys.path`` (sitecustomize mechanism).
The Docker image copies all packages into /app, so no extra path is needed
inside containers.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
