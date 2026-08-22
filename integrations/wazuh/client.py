"""Wazuh API client (spec §28) — minimal, token-based client.

Only the endpoints SecFlow needs:
  - authenticate (JWT)
  - /security/events (alerts)
  - / (health)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ALERTS_ENDPOINT = "/security/events"


class WazuhError(RuntimeError):
    pass


class WazuhClient:
    def __init__(
        self,
        base_url: str = "",
        username: str = "",
        password: str = "",
        verify_ssl: bool | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.wazuh_url).rstrip("/")
        self.username = username or settings.wazuh_username
        self.password = password or settings.wazuh_password
        self.verify_ssl = settings.wazuh_verify_ssl if verify_ssl is None else verify_ssl
        self.timeout = timeout
        self._token: str | None = None
        self._token_expires: datetime | None = None

    # ------------------------------------------------------------------
    def authenticate(self) -> str:
        """Obtain (and cache) a JWT from Wazuh's auth endpoint."""
        if self._token and self._token_expires and self._token_expires > datetime.now(timezone.utc):
            return self._token
        if not self.base_url or not self.username or not self.password:
            raise WazuhError("Wazuh URL/username/password not configured")
        try:
            r = httpx.post(
                f"{self.base_url}/security/user/authenticate",
                auth=(self.username, self.password),
                verify=self.verify_ssl,
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            raise WazuhError(f"Wazuh authentication failed: {exc}") from exc
        token = data.get("data", {}).get("token") or data.get("token")
        if not token:
            raise WazuhError("Wazuh auth response missing token")
        self._token = token
        self._token_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        return token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.authenticate()}"}

    # ------------------------------------------------------------------
    def get_alerts(self, since: datetime | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch security events, newest first, optionally since a timestamp."""
        params: dict[str, Any] = {"limit": limit, "sort": "-timestamp"}
        if since:
            params["q"] = f"timestamp>{since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        try:
            r = httpx.get(
                f"{self.base_url}{ALERTS_ENDPOINT}",
                headers=self._headers(),
                params=params,
                verify=self.verify_ssl,
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            raise WazuhError(f"Wazuh alerts request failed: {exc}") from exc
        return data.get("data", {}).get("affected_items", [])

    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/", timeout=5, verify=self.verify_ssl)
            return {"ok": r.status_code == 200, "status_code": r.status_code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
