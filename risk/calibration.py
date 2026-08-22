"""Risk Engine calibration — the single place to tune factors.

These values must be validated against `datasets/evaluation/` (see
`ai/evaluators/evaluate.py`) instead of being tuned ad-hoc.
"""
from __future__ import annotations

# Technical severity → multiplier
SEVERITY_FACTORS: dict[str, float] = {
    "info": 0.5,
    "low": 1.0,
    "medium": 2.0,
    "high": 3.5,
    "critical": 5.0,
}

# Asset criticality (1..5) → multiplier
ASSET_CRITICALITY_FACTORS: dict[int, float] = {
    1: 1.0,
    2: 1.2,
    3: 1.5,
    4: 1.8,
    5: 2.2,
}

# Environment exposure → multiplier
EXPOSURE_FACTORS: dict[str, float] = {
    "production": 1.4,
    "dmz": 1.3,
    "staging": 1.1,
    "internal": 1.0,
    "test": 0.8,
    "development": 0.8,
}

# Threat intel confirmation boost
THREAT_INTEL_FACTOR: float = 1.3

# Exploit evidence / PoC availability boost
EXPLOIT_FACTOR: float = 1.5

# Confidence mapping range (low, high)
CONFIDENCE_WEIGHT: tuple[float, float] = (0.5, 1.0)

# (level, inclusive_low, exclusive_high)
RISK_LEVELS: list[tuple[str, float, float]] = [
    ("low", 0.0, 5.0),
    ("medium", 5.0, 10.0),
    ("high", 10.0, 20.0),
    ("critical", 20.0, float("inf")),
]
