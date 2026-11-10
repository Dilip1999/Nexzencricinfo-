"""Cricket Database API adapter (https://cricketdatabase.com).

Uses Bearer authentication and the provider's /v1 REST API. Never logs the key.
The free plan does not include live endpoints; a plan restriction is surfaced
as a provider error rather than silently treated as empty data.
"""
from __future__ import annotations
import os
from typing import Any
import requests

API_ROOT = "https://api.cricketdatabase.com/v1"
DEFAULT_TIMEOUT = 20

class CricketDataError(RuntimeError):
    """Raised for provider errors, plan restrictions or malformed responses."""

class CricketDataClient:
    def __init__(self, api_key: str | None = None, *, session=None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = (api_key if api_key is not None else os.getenv("CRICKETDATA_API_KEY", "")).strip()
        self.session = session or requests.Session()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        if not self.api_key:
            raise CricketDataError("CRICKETDATA_API_KEY is not configured.")
        if not path or path.startswith("/") or ".." in path:
            raise ValueError("Endpoint must be a safe API path.")
        response = self.session.get(
            f"{API_ROOT}/{path}",
            params=params,
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            # Do not include request URL or headers: credentials must never enter logs.
            raise CricketDataError(f"Cricket Database HTTP error: {response.status_code}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise CricketDataError("Provider returned invalid JSON.") from exc
        if not isinstance(payload, dict) or "data" not in payload:
            raise CricketDataError("Provider response must be an object containing data.")
        error = payload.get("error")
        if error:
            if isinstance(error, dict):
                message = error.get("message") or error.get("code") or "Provider request failed"
            else:
                message = str(error)
            raise CricketDataError(str(message)[:300])
        return payload

    def matches(self, **filters: Any) -> dict[str, Any]:
        """List matches; free key covers full recent window and samples older archive."""
        return self._get("matches", **filters)

    def results_yesterday(self) -> dict[str, Any]:
        return self._get("results/yesterday")

    def match(self, match: str) -> dict[str, Any]:
        return self._get(f"matches/{_valid_slug(match)}")

    def scorecard(self, match: str) -> dict[str, Any]:
        return self._get(f"matches/{_valid_slug(match)}/scorecard")

    def player_stats(self, player: str) -> dict[str, Any]:
        return self._get(f"players/{_valid_slug(player)}/stats")

    def player_search(self, query: str) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("Player search text is required.")
        return self._get("search", q=query.strip())

    def live_matches(self, **filters: Any) -> dict[str, Any]:
        """Available on Match Week, Pro and Analyst Pro; not the Free plan."""
        return self._get("live", **filters)

def _valid_slug(value: str) -> str:
    cleaned = str(value).strip()
    if not cleaned or len(cleaned) > 200 or "/" in cleaned or ".." in cleaned:
        raise ValueError("A valid provider resource address is required.")
    return cleaned
