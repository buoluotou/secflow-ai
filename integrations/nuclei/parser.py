"""Nuclei JSONL parser — one line → NucleiResult."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from integrations.nuclei.models import NucleiResult


def parse_line(line: str) -> NucleiResult | None:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    # nuclei JSONL uses hyphenated keys (template-id, matched-at, ...)
    if isinstance(data, dict):
        data = {k.replace("-", "_"): v for k, v in data.items()}
    return NucleiResult.model_validate(data)


def parse_jsonl(path: str | Path) -> list[NucleiResult]:
    results: list[NucleiResult] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            r = parse_line(line)
            if r and r.info.severity:
                results.append(r)
    return results


def iter_jsonl_text(text: str) -> Iterator[NucleiResult]:
    for line in text.splitlines():
        r = parse_line(line)
        if r:
            yield r
