"""AI evaluation harness (spec §54).

Loads cases from datasets/evaluation/, runs the Triage Agent on each input,
compares against expected labels and computes:

  Precision, Recall, F1, False Positive Rate,
  Evidence Coverage, Hallucination Rate

Usage:
    python -m ai.evaluators.evaluate [--provider mock|openai|ollama] [--cases dir]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai.agents import create_agent
from ai.models.config import LLMConfig

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CASES = REPO_ROOT / "datasets" / "evaluation"

POSITIVE_CLASSES = {"true_positive", "likely_true_positive"}


def load_cases(cases_dir: Path) -> list[dict]:
    out = []
    for p in sorted(cases_dir.glob("*.json")):
        if p.name.startswith("_"):
            continue
        with p.open(encoding="utf-8") as f:
            case = json.load(f)
            case["_file"] = p.name
            out.append(case)
    return out


def run_case(agent, case: dict) -> dict:
    context = dict(case["input"])
    # evidence ids referenced in the case must be in the context envelope
    out = agent.run(context)
    expected_positive = case.get("expected_classification") in POSITIVE_CLASSES
    actual_positive = out.get("classification") in POSITIVE_CLASSES
    expected_sev = case.get("expected_severity")
    actual_sev = out.get("severity")
    expected_techniques = set(case.get("expected_techniques") or [])
    actual_techniques = set(out.get("mitre_techniques") or [])
    referenced = set(out.get("evidence_ids") or [])
    available = {e.get("id") for e in context.get("evidence", [])}

    return {
        "case_id": case.get("case_id"),
        "file": case.get("_file"),
        "expected_classification": case.get("expected_classification"),
        "actual_classification": out.get("classification"),
        "expected_positive": expected_positive,
        "actual_positive": actual_positive,
        "severity_match": expected_sev is None or expected_sev == actual_sev,
        "technique_recall": (
            len(expected_techniques & actual_techniques) / len(expected_techniques)
            if expected_techniques
            else 1.0
        ),
        "evidence_coverage": (
            len(referenced & available) / len(referenced) if referenced else 1.0
        ),
        "hallucinated_evidence": sorted(referenced - available),
        "output": out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SecFlow AI evaluation harness")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    if not cases:
        print("No evaluation cases found.", file=sys.stderr)
        return 1

    if args.provider:
        config = LLMConfig.from_env()
        config.provider = args.provider
        from ai.models.llm import LLMClient

        llm = LLMClient(config)
    else:
        llm = None

    agent = create_agent("triage", llm=llm)
    results = [run_case(agent, c) for c in cases]

    n = len(results)
    tp = sum(1 for r in results if r["expected_positive"] and r["actual_positive"])
    fp = sum(1 for r in results if not r["expected_positive"] and r["actual_positive"])
    fn = sum(1 for r in results if r["expected_positive"] and not r["actual_positive"])
    tn = sum(1 for r in results if not r["expected_positive"] and not r["actual_positive"])

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    evidence_coverage = sum(r["evidence_coverage"] for r in results) / n
    hallucination_rate = sum(len(r["hallucinated_evidence"]) for r in results) / n

    metrics = {
        "cases": n,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "evidence_coverage": round(evidence_coverage, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "severity_match_rate": round(
            sum(1 for r in results if r["severity_match"]) / n, 4
        ),
        "technique_recall": round(
            sum(r["technique_recall"] for r in results) / n, 4
        ),
        "provider": agent.llm.provider,
        "model": agent.llm.config.model,
    }

    out_path = REPO_ROOT / "datasets" / "evaluation" / "_metrics.json"
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    for r in results:
        flag = "PASS" if (
            r["expected_positive"] == r["actual_positive"]
            and r["severity_match"]
            and not r["hallucinated_evidence"]
        ) else "FAIL"
        print(f"  [{flag}] {r['case_id']} expected={r['expected_classification']} "
              f"actual={r['actual_classification']} sev_match={r['severity_match']} "
              f"hallucinated={r['hallucinated_evidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
