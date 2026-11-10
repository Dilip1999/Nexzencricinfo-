"""CricketData.org (CricAPI) adapter.

API key is supplied only at request time from CRICKETDATA_API_KEY. Never commit
credentials. The provider documents key-in-query authentication; callers must
avoid logging full request URLs because they contain the key.
"""
from __future__ import annotations
import os
from typing import Any
from urllib.parse import urlparse
import requests

API_ROOT = "https://api.cricapi.com/v1"
DEFAULT_TIMEOUT = 20

class CricketDataError(RuntimeError):
    """Raised for provider errors or malformed responses."""

class CricketDataClient:
    def __init__(self, api_key: str | None = None, *, session=None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = (api_key if api_key is not None else os.getenv("CRICKETDATA_API_KEY", "")).strip()
        self.session = session or requests.Session()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        if not self.api_key:
            raise CricketDataError("CRICKETDATA_API_KEY is not configured.")
        if endpoint.startswith("/") or ".." in endpoint:
            raise ValueError("Endpoint must be a safe API path.")
        response = self.session.get(
            f"{API_ROOT}/{endpoint}",
            params={"apikey": self.api_key, **params},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise CricketDataError("Provider returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise CricketDataError("Provider response must be a JSON object.")
        status = str(payload.get("status", "")).lower()
        if status and status not in ("success", "ok"):
            message = str(payload.get("reason") or payload.get("message") or "Provider reported failure")
            raise CricketDataError(message[:300])
        if "data" not in payload:
            raise CricketDataError("Provider response is missing the data field.")
        return payload

    def matches(self, offset: int = 0) -> dict[str, Any]:
        return self._get("matches", offset=_valid_offset(offset))

    def series(self, offset: int = 0, search: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"offset": _valid_offset(offset)}
        if search and search.strip():
            params["search"] = search.strip()
        return self._get("series", **params)

    def player_search(self, search: str, offset: int = 0) -> dict[str, Any]:
        if not search.strip():
            raise ValueError("Player search text is required.")
        return self._get("players", offset=_valid_offset(offset), search=search.strip())

    def scorecard(self, match_id: str) -> dict[str, Any]:
        return self._get("match_scorecard", id=_valid_id(match_id))

    def squad(self, match_id: str) -> dict[str, Any]:
        # Provider documents this Fantasy endpoint; availability may depend on plan.
        return self._get("match_squad", id=_valid_id(match_id))

def _valid_offset(offset: int) -> int:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer.")
    return offset

def _valid_id(value: str) -> str:
    cleaned = str(value).strip()
    if not cleaned or len(cleaned) > 200:
        raise ValueError("A valid provider resource ID is required.")
    return cleaned
