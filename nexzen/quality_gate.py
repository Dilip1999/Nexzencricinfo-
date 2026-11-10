"""Deterministic scorecard integrity checks. Warnings require editorial review; errors block use."""
from __future__ import annotations
from typing import Any

def validate_analysis_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    innings_list = report.get("innings")
    if not isinstance(innings_list, list) or not innings_list:
        return {"status":"blocked","publish_eligible":False,"errors":["No innings are available."],"warnings":[]}
    for idx, innings in enumerate(innings_list, start=1):
        prefix = f"Innings {idx}"
        batting = innings.get("batting_card")
        bowling = innings.get("bowling_card")
        if not isinstance(batting, list) or not batting:
            errors.append(f"{prefix}: missing batting card.")
            batting = []
        if not isinstance(bowling, list) or not bowling:
            warnings.append(f"{prefix}: missing full bowling card.")
            bowling = []
        total = innings.get("runs")
        wickets = innings.get("wickets")
        if not isinstance(total, int) or total < 0:
            errors.append(f"{prefix}: invalid innings total.")
        if not isinstance(wickets, int) or not 0 <= wickets <= 10:
            errors.append(f"{prefix}: invalid wicket count.")
        batting_runs = sum(_safe_nonnegative(row.get("runs")) for row in batting)
        if isinstance(total, int) and batting_runs > total:
            errors.append(f"{prefix}: batter runs exceed innings total.")
        elif isinstance(total, int) and batting_runs < total:
            extras = innings.get("extras")
            if isinstance(extras, (int, float)) and batting_runs + extras == total:
                pass
            else:
                warnings.append(f"{prefix}: batting runs do not reconcile to total; extras are missing or inconsistent.")
        dismissed = sum(1 for row in batting if row.get("out") is True)
        if isinstance(wickets, int) and dismissed != wickets:
            warnings.append(f"{prefix}: dismissed batter count differs from innings wickets.")
        legal_balls = sum(_overs_balls(row.get("overs")) for row in bowling)
        expected_balls = _overs_balls(innings.get("overs"))
        if expected_balls is not None and bowling and legal_balls != expected_balls:
            warnings.append(f"{prefix}: bowling legal-ball total does not match innings overs.")
        if bowling and isinstance(total, int):
            conceded = sum(_safe_nonnegative(row.get("runs_conceded", row.get("runs"))) for row in bowling)
            if conceded > total:
                warnings.append(f"{prefix}: bowler-conceded runs exceed innings total; check extras and provider definitions.")
        if bowling:
            expected = sorted(bowling, key=lambda row: (
                _safe_nonnegative(row.get("wickets")),
                -float(row.get("economy") if row.get("economy") is not None else 9999)
            ), reverse=True)[:3]
            # Better economy breaks wicket ties; normalize to canonical ordering below.
            expected = sorted(bowling, key=lambda row: (-_safe_nonnegative(row.get("wickets")),
                float(row.get("economy") if row.get("economy") is not None else 9999)))[:3]
            summary = innings.get("bowling_figures")
            if isinstance(summary, list) and [x.get("player_id") for x in summary] != [x.get("player_id") for x in expected]:
                warnings.append(f"{prefix}: bowling leaders summary does not match the full bowling card.")
    if not report.get("source_url"):
        warnings.append("Source URL is missing.")
    context = report.get("match_listing_context") or {}
    if context.get("format") and context.get("competition"):
        fmt = str(context["format"]).lower()
        comp = str(context["competition"]).lower()
        if "t10" in comp and fmt not in ("t10", "10-over", "10 overs"):
            warnings.append("Match format conflicts with competition label; confirm with provider before publication.")
    status = "blocked" if errors else ("needs_human_review" if warnings else "validated")
    return {"status":status,"publish_eligible":status == "validated","errors":errors,"warnings":warnings}

def _safe_nonnegative(value: Any) -> int:
    try:
        number = int(value)
        return number if number >= 0 else 0
    except (TypeError, ValueError):
        return 0

def _overs_balls(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        text = str(value)
        if "." in text:
            whole, balls = text.split(".", 1)
            if not whole.isdigit() or not balls.isdigit() or int(balls) > 5:
                return None
            return int(whole) * 6 + int(balls)
        return int(text) * 6 if text.isdigit() else None
    except (TypeError, ValueError):
        return None
