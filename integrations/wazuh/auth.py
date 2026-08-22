"""Wazuh auth helpers — thin wrapper around the client token logic
(kept as a module so the spec §28 layout is honoured)."""
from __future__ import annotations

from integrations.wazuh.client import WazuhClient, WazuhError


def get_token(base_url: str, username: str, password: str) -> str:
    client = WazuhClient(base_url, username, password)
    return client.authenticate()
