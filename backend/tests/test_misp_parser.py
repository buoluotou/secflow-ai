"""MISP parser tests (spec §30)."""
from integrations.misp.mapper import map_to_ioc
from integrations.misp.parser import event_to_iocs


def _event():
    return {
        "id": "42",
        "uuid": "evt-uuid",
        "info": "Suspicious activity",
        "tags": [{"name": "tlp:red"}, {"name": "apt:test"}],
        "Attribute": [
            {"id": "1", "uuid": "attr-1", "type": "ip-src", "value": "203.0.113.66", "to_ids": True, "category": "Network activity"},
            {"id": "2", "uuid": "attr-2", "type": "domain", "value": "evil.example.com", "to_ids": False, "category": "Network activity"},
            {"id": "3", "uuid": "attr-3", "type": "sha256", "value": "deadbeef" * 8, "to_ids": True, "category": "Payload delivery"},
            {"id": "4", "uuid": "attr-4", "type": "email-src", "value": "phish@evil.example.com", "to_ids": True, "category": "Payload delivery"},
        ],
    }


def test_event_to_iocs():
    iocs = event_to_iocs(_event())
    types = {i["type"] for i in iocs}
    assert types == {"ip", "domain", "hash", "email"}
    ip = next(i for i in iocs if i["type"] == "ip")
    assert ip["value"] == "203.0.113.66"
    assert ip["confidence"] == 0.8  # to_ids=True
    assert "tlp:red" in ip["tags"]


def test_map_to_ioc():
    mapped = map_to_ioc({"type": "ip", "value": "1.2.3.4", "confidence": 0.9, "tags": ["t"], "external_id": "x"})
    assert mapped["source"] == "misp"
    assert mapped["external_id"] == "x"
