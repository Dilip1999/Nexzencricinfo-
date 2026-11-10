"""Normalize Cricket Database scorecards into evidence-preserving analysis summaries."""
from __future__ import annotations
from typing import Any

def overs_to_balls(overs: str | int | float) -> int:
    text = str(overs).strip()
    if "." in text:
        whole, balls = text.split(".", 1)
        if not whole.isdigit() or not balls.isdigit() or int(balls) > 5:
            raise ValueError(f"Invalid cricket overs notation: {text}")
        return int(whole) * 6 + int(balls)
    if not text.isdigit():
        raise ValueError(f"Invalid cricket overs notation: {text}")
    return int(text) * 6

def _number(value: Any, field: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric scorecard field: {field}") from exc
    if result < 0:
        raise ValueError(f"Negative scorecard field: {field}")
    return result

def analyze_scorecard(payload: dict[str, Any], *, source_url: str) -> dict[str, Any]:
    """Return per-innings leaders and derived rates; does not infer match winner or narrative."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("Expected Cricket Database scorecard response with object data.")
    data = payload["data"]
    innings_list = data.get("innings")
    if not isinstance(innings_list, list) or not innings_list:
        raise ValueError("Scorecard contains no innings.")
    summaries = []
    for item in innings_list:
        batting = item.get("batting") or []
        bowling = item.get("bowling") or []
        if not isinstance(batting, list) or not isinstance(bowling, list):
            raise ValueError("Invalid batting or bowling section.")
        batters = []
        for row in batting:
            runs = _number(row.get("runs", 0), "batting.runs")
            balls = _number(row.get("balls", 0), "batting.balls")
            fours = _number(row.get("fours", 0), "batting.fours")
            sixes = _number(row.get("sixes", 0), "batting.sixes")
            batters.append({
                "player_id": row.get("player"), "name": row.get("name", "Unknown batter"),
                "runs": runs, "balls": balls, "fours": fours, "sixes": sixes,
                "strike_rate": round(100 * runs / balls, 2) if balls else None,
                "dismissal": row.get("dismissal"), "out": row.get("out"),
            })
        bowlers = []
        for row in bowling:
            balls = overs_to_balls(row.get("overs", "0"))
            conceded = _number(row.get("runs", 0), "bowling.runs")
            wickets = _number(row.get("wickets", 0), "bowling.wickets")
            bowlers.append({
                "player_id": row.get("player"), "name": row.get("name", "Unknown bowler"),
                "overs": str(row.get("overs", "0")), "legal_balls": balls,
                "runs_conceded": conceded, "wickets": wickets,
                "economy": round(conceded * 6 / balls, 2) if balls else None,
            })
        summaries.append({
            "innings": item.get("innings"), "team": item.get("name") or item.get("team"),
            "runs": _number(item.get("runs", 0), "innings.runs"),
            "wickets": _number(item.get("wickets", 0), "innings.wickets"),
            "overs": str(item.get("overs", "")), "run_rate": item.get("run_rate"),
            "top_scorers": sorted(batters, key=lambda x: (x["runs"], x["balls"]), reverse=True)[:3],
            "bowling_figures": sorted(bowlers, key=lambda x: (x["wickets"], -(x["economy"] if x["economy"] is not None else 999)))[:3],
            "batting_card": batters, "bowling_card": bowlers,
        })
    return {
        "provider": "Cricket Database",
        "source_url": source_url,
        "match": data.get("match"),
        "result": data.get("result"),
        "innings": summaries,
        "weather": data.get("weather", []),
        "editorial_status": "data_ready_for_human_review",
        "limitations": ["This is a match scorecard summary, not career performance.", "Do not infer a confirmed playing XI from a scorecard.", "Verify match date, format and competition before publication."],
    }
