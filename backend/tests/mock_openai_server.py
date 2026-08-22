"""Test-only OpenAI-compatible mock server (validates the LLM provider path).

Run: uvicorn tests.mock_openai_server:app --port 8097
"""  # noqa: E501
import json, re
from fastapi import FastAPI, Request

app = FastAPI()

def _real_evidence_ids(user: str) -> list[str]:
    """提取 user prompt 中上下文里真实存在的 evidence ids"""
    m = re.search(r'"evidence":\s*(\[.*?\])', user)
    if not m:
        return []
    try:
        evs = json.loads(m.group(1))
        return [e["id"] for e in evs[:2] if isinstance(e, dict) and e.get("id")]
    except Exception:
        return []

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    user = body["messages"][-1]["content"]
    ev = _real_evidence_ids(user)
    if "AGENT: triage" in user:
        content = {
            "classification": "true_positive",
            "severity": "high",
            "confidence": 0.91,
            "attack_stage": "execution",
            "mitre_techniques": ["T1059.001"],
            "evidence_ids": ev,
            "reasoning_summary": "OpenAI-mock: 高危事件且命中恶意 IOC，判定为真实攻击，证据已绑定。",
            "recommendations": ["block_src_ip", "review_related_events"],
        }
    elif "AGENT: threat" in user:
        content = {"malicious": True, "confidence": 0.88, "tags": ["mock-apt"], "related_entities": [], "evidence_ids": ev}
    elif "AGENT: vuln" in user:
        content = {"authenticity": "confirmed", "remediation_priority": "high", "impact_scope": ["web"], "exploit_risk": 0.7, "evidence_ids": ev}
    else:
        content = {"summary": "mock report", "timeline_narrative": "mock", "recommendations": ["review"], "evidence_ids": ev}
    return {"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}
