"""Nuclei JSONL parser tests (spec §29)."""
import json

from integrations.nuclei.mapper import map_to_finding
from integrations.nuclei.parser import parse_jsonl


def _line(template="http-vuln-test", sev="high"):
    return json.dumps(
        {
            "template-id": template,
            "info": {
                "name": "Test RCE",
                "severity": sev,
                "description": "A test vulnerability",
                "classification": {"cwe-id": ["CWE-78"], "cvss-score": 9.1},
                "remediation": "Patch it",
            },
            "matched-at": "http://demo-web",
            "host": "demo-web",
            "request": "GET / HTTP/1.1",
            "response": "HTTP/1.1 200 OK",
            "matcher-status": True,
            "extracted-results": ["uid=0(root)"],
        }
    )


def test_parse_and_map_jsonl(tmp_path):
    p = tmp_path / "out.jsonl"
    p.write_text(_line() + "\n" + _line(sev="low") + "\nnot-json\n", encoding="utf-8")
    results = parse_jsonl(p)
    assert len(results) == 2

    finding = map_to_finding(results[0])
    assert finding["source"] == "nuclei"
    assert finding["template_id"] == "http-vuln-test"
    assert finding["severity"] == "high"
    assert finding["cvss"] == 9.1
    assert finding["cwe"] == "CWE-78"
    assert finding["evidence"] == "uid=0(root)"
    assert finding["external_id"].startswith("http-vuln-test:")
