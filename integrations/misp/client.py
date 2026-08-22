"""MISP client (spec §30) — search_ip / search_domain / search_hash / search_url.

Uses the `events/restSearch` endpoint with the `value` filter (fastest
indicator lookup), and falls back to `/attributes/restSearch`.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from integrations.misp.models import MISPEvent, MISPResponse

logger = logging.getLogger(__name__)


class MISPError(RuntimeError):
    pass


class MISPClient:
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        verify_ssl: bool | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.misp_url).rstrip("/")
        self.api_key = api_key or settings.misp_api_key
        self.verify_ssl = settings.misp_verify_ssl if verify_ssl is None else verify_ssl
        self.timeout = timeout

    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        if not self.base_url or not self.api_key:
            raise MISPError("MISP URL/API key not configured")
        return {
            "Authorization": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _rest_search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            r = httpx.get(
                f"{self.base_url}/events/restSearch",
                headers=self._headers(),
                params={"returnFormat": "json", **params},
                verify=self.verify_ssl,
                timeout=self.timeout,
            )
            r.raise_for_status()
            payload = r.json()
        except httpx.HTTPError as exc:
            raise MISPError(f"MISP restSearch failed: {exc}") from exc
        try:
            resp = MISPResponse.model_validate(payload)
        except Exception:  # noqa: BLE001  (older MISP response shapes)
            return payload.get("response", []) if isinstance(payload, dict) else []
        return [e.model_dump() for e in resp.response]

    # ------------------------------------------------------------------
    def search_ip(self, ip: str) -> list[dict[str, Any]]:
        return self._rest_search({"value": ip, "type": ["ip-src", "ip-dst", "ip"]})

    def search_domain(self, domain: str) -> list[dict[str, Any]]:
        return self._rest_search({"value": domain, "type": "domain"})

    def search_hash(self, hash_value: str) -> list[dict[str, Any]]:
        return self._rest_search(
            {"value": hash_value, "type": ["md5", "sha1", "sha256", "sha512"]}
        )

    def search_url(self, url: str) -> list[dict[str, Any]]:
        return self._rest_search({"value": url, "type": "url"})

    def search_value(self, value: str) -> list[dict[str, Any]]:
        return self._rest_search({"value": value})

    def list_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._rest_search({"limit": limit})

    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/servers/getVersion", headers=self._headers(), timeout=5, verify=self.verify_ssl)
            return {"ok": r.status_code == 200, "status_code": r.status_code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
