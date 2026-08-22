"""Nuclei runner (spec §15, §29) — scan jobs execute nuclei on demand.

Two modes:
  - docker : `docker run --rm -v ... projectdiscovery/nuclei` (default)
  - binary : invoke a local `nuclei` binary

Output is parsed as JSONL and mapped to Findings by the worker.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class NucleiRunError(RuntimeError):
    pass


def build_command(targets: list[str], options: dict[str, Any]) -> list[str]:
    mode = options.get("mode") or settings.nuclei_mode
    if mode == "docker":
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{tempfile.gettempdir()}:/data",
            settings.nuclei_image,
            "-jsonl", "-silent",
        ]
        if settings.nuclei_template_dir:
            cmd += ["-t", settings.nuclei_template_dir]
    else:
        cmd = [settings.nuclei_bin, "-jsonl", "-silent"]
        if settings.nuclei_template_dir:
            cmd += ["-t", settings.nuclei_template_dir]
    if options.get("templates"):
        cmd += ["-t", options["templates"]]
    if options.get("tags"):
        cmd += ["-tags", options["tags"]]
    if options.get("severity"):
        cmd += ["-severity", options["severity"]]
    cmd += ["-c", str(options.get("concurrency") or settings.nuclei_concurrency)]
    cmd += ["-o", "/data/secflow_nuclei.jsonl"] if mode == "docker" else ["-o", "/tmp/secflow_nuclei.jsonl"]
    cmd += targets
    return cmd


def run(targets: list[str], options: dict[str, Any] | None = None) -> list[dict]:
    """Run nuclei and return parsed JSONL results (list of dicts)."""
    options = options or {}
    cmd = build_command(targets, options)
    out_file = Path("/tmp/secflow_nuclei.jsonl")
    mode = options.get("mode") or settings.nuclei_mode

    if mode == "docker" and shutil.which("docker") is None:
        raise NucleiRunError("docker not available on host (required for nuclei docker mode)")

    logger.info("running nuclei: %s", " ".join(cmd[:8]) + " ...")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=options.get("timeout", 1800))
    if proc.returncode != 0 and proc.returncode != 1:  # nuclei exits 1 when no results
        raise NucleiRunError(f"nuclei exited {proc.returncode}: {proc.stderr[-500:]}")

    results: list[dict] = []
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        out_file.unlink(missing_ok=True)
    return results


def is_available() -> bool:
    if settings.nuclei_mode == "docker":
        return shutil.which("docker") is not None
    return shutil.which(settings.nuclei_bin) is not None
