"""Small authenticated client for OpenCricketAPI match data."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

import requests

API_ROOT = os.getenv("OPENCRICKET_API_BASE_URL", "https://api.opencricketapi.com").rstrip("/")
MATCHES_PATH = "/v1/matches"
TIMEOUT = 25


def fetch_matches(limit: int = 30) -> list[dict[str, Any]]:
    """Fetch a recent batch. The API token is only sent in the Authorization header."""
    token = os.getenv("OPENCRICKET_API_KEY", "").strip()
    if not token:
        print("OPENCRICKET_API_KEY is not configured; skipping OpenCricket.")
        return []
    response = requests.get(
        f"{API_ROOT}{MATCHES_PATH}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={"limit": limit},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    records = payload.get("data", [])
    if not isinstance(records, list):
        raise ValueError("OpenCricket API response field 'data' was not a list.")
    return [record for record in records if isinstance(record, dict)]


def match_to_article(match: dict[str, Any]) -> dict[str, str] | None:
    """Turn a completed, recent match into a concise attributed draft item."""
    result = str(match.get("result") or "").strip()
    if not result:
        return None
    date_text = str(match.get("date") or "")[:10]
    try:
        match_date = date.fromisoformat(date_text)
    except ValueError:
        return None
    # Avoid presenting old archive records as today's news.
    if match_date < date.today() - timedelta(days=4) or match_date > date.today() + timedelta(days=1):
        return None

    teams = match.get("teams") or []
    names = []
    if isinstance(teams, list):
        for team in teams:
            if isinstance(team, dict) and team.get("name"):
                names.append(str(team["name"]))
    matchup = " vs ".join(names[:2]) or "Cricket match"
    competition = match.get("competition") or {}
    competition_name = competition.get("name", "") if isinstance(competition, dict) else str(competition)
    stage = str(match.get("stage") or "").strip()
    venue = match.get("venue") or {}
    venue_name = venue.get("name", "") if isinstance(venue, dict) else str(venue)
    title = f"{matchup}: {result}"
    details = [part for part in (competition_name, stage, venue_name, f"Match date: {date_text}") if part]
    source_url = str(match.get("source_url") or match.get("url") or "https://opencricketapi.com")
    return {
        "title": title,
        "url": source_url,
        "summary": " • ".join(details) + " • Match data: OpenCricketAPI",
        "source": "OpenCricketAPI",
    }
