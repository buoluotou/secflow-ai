"""Nuclei runner (spec §15, §29) — scan jobs execute nuclei on demand.

Three modes:
  - docker : `docker run --rm -v ... projectdiscovery/nuclei` (default)
  - binary : invoke a local `nuclei` binary
  - mock   : offline demo mode — synthesizes realistic JSONL results so the
             full scan pipeline (job → worker → finding → correlation) can
             be exercised on machines without network access / nuclei image
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
    if (options.get("mode") or settings.nuclei_mode) == "mock":
        return _mock_scan(targets, options)
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


def _mock_scan(targets: list[str], options: dict[str, Any]) -> list[dict]:
    """Deterministic offline results for demo/CI (NUCLEI_MODE=mock)."""
    sev = options.get("severity") or "high"
    templates = [
        {
            "template-id": "http-missing-security-headers",
            "info": {"name": "Missing Security Headers", "severity": "low",
                     "description": "Response is missing common security headers.",
                     "classification": {"cwe-id": ["CWE-693"]}, "remediation": "Add security headers."},
        },
        {
            "template-id": "ssl-tls-detect",
            "info": {"name": "SSL/TLS Outdated Protocol", "severity": "medium",
                     "description": "Server supports outdated TLS versions.",
                     "classification": {"cwe-id": ["CWE-326"], "cvss-score": 5.3},
                     "remediation": "Disable TLS 1.0/1.1."},
        },
        {
            "template-id": "http-vuln-test-rce",
            "info": {"name": "Test RCE (Demo)", "severity": "high",
                     "description": "Demo vulnerability template used for offline scans.",
                     "classification": {"cwe-id": ["CWE-78"], "cvss-score": 8.1},
                     "remediation": "Apply vendor patch."},
        },
    ]
    results: list[dict] = []
    for i, t in enumerate(templates):
        if t["info"]["severity"] != sev and sev != "all":
            continue
        target = targets[0] if targets else "http://demo.local"
        results.append({
            "template-id": t["template-id"],
            "info": t["info"],
            "matched-at": target,
            "host": target.replace("http://", "").replace("https://", "").split("/")[0],
            "request": f"GET {target}/ HTTP/1.1",
            "response": "HTTP/1.1 200 OK\r\nServer: nginx/1.14",
            "matcher-status": True,
            "extracted-results": [f"demo-match-{i}"],
            "timestamp": "2026-01-01T00:00:00Z",
        })
    logger.info("nuclei mock scan: %s synthetic findings", len(results))
    return results


def is_available() -> bool:
    mode = settings.nuclei_mode
    if mode == "mock":
        return True
    if mode == "docker":
        return shutil.which("docker") is not None
    return shutil.which(settings.nuclei_bin) is not None
