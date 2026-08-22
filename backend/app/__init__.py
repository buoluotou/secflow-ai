"""SecFlow AI backend application package.

Monorepo path bootstrap: repo-root packages (``ai``, ``integrations``,
``risk``, ``reports``) are made importable no matter how the app is launched
(uvicorn binary, ``python -m uvicorn``, celery, pytest). Inside Docker all
packages are copied to /app so this is a no-op.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
