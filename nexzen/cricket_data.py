"""Provider-neutral cricket data contracts. Values must come from a cited scorecard/provider."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class BattingInnings:
    player: str
    runs: int
    balls: int
    fours: int = 0
    sixes: int = 0
    not_out: bool = False
    def __post_init__(self):
        if not self.player.strip() or min(self.runs, self.balls, self.fours, self.sixes) < 0:
            raise ValueError("Player is required and batting values cannot be negative.")
        if self.balls == 0 and self.runs > 0:
            raise ValueError("A batter cannot score runs from zero balls faced.")

@dataclass(frozen=True)
class BowlingSpell:
    player: str
    legal_balls: int
    runs_conceded: int
    wickets: int
    def __post_init__(self):
        if not self.player.strip() or min(self.legal_balls, self.runs_conceded, self.wickets) < 0:
            raise ValueError("Player is required and bowling values cannot be negative.")

@dataclass(frozen=True)
class PlayerBattingAggregate:
    player: str
    runs: int
    innings: int
    dismissals: int
    balls: int
    fours: int = 0
    sixes: int = 0

@dataclass(frozen=True)
class PlayerBowlingAggregate:
    player: str
    runs_conceded: int
    wickets: int
    legal_balls: int

def batting_average(runs: int, dismissals: int) -> float | None:
    if runs < 0 or dismissals < 0: raise ValueError("Inputs cannot be negative.")
    return round(runs / dismissals, 2) if dismissals else None

def strike_rate(runs: int, balls: int) -> float | None:
    if runs < 0 or balls < 0: raise ValueError("Inputs cannot be negative.")
    return round(100 * runs / balls, 2) if balls else None

def bowling_economy(runs_conceded: int, legal_balls: int) -> float | None:
    if runs_conceded < 0 or legal_balls < 0: raise ValueError("Inputs cannot be negative.")
    return round(runs_conceded * 6 / legal_balls, 2) if legal_balls else None

def bowling_average(runs_conceded: int, wickets: int) -> float | None:
    if runs_conceded < 0 or wickets < 0: raise ValueError("Inputs cannot be negative.")
    return round(runs_conceded / wickets, 2) if wickets else None

def overs_from_balls(legal_balls: int) -> str:
    if legal_balls < 0: raise ValueError("Legal balls cannot be negative.")
    return f"{legal_balls // 6}.{legal_balls % 6}"

def compare_batters(a: PlayerBattingAggregate, b: PlayerBattingAggregate) -> dict:
    """Return metrics without declaring a winner; callers must align format and sample."""
    return {
        a.player: {"runs": a.runs, "average": batting_average(a.runs, a.dismissals), "strike_rate": strike_rate(a.runs, a.balls), "innings": a.innings},
        b.player: {"runs": b.runs, "average": batting_average(b.runs, b.dismissals), "strike_rate": strike_rate(b.runs, b.balls), "innings": b.innings},
        "comparison_context_required": ["format", "competition", "date_range", "sample_size", "source"],
    }

def squad_balance(players: Iterable[dict]) -> dict:
    """Summarise declared squad roles; does not infer a playing XI."""
    roster = list(players)
    roles = ("batter", "wicketkeeper", "all_rounder", "bowler")
    counts = {role: 0 for role in roles}
    names = set()
    for item in roster:
        name, role = str(item.get("name", "")).strip(), str(item.get("role", "")).lower()
        if not name or role not in roles:
            raise ValueError("Each squad member needs a name and one supported role.")
        if name.casefold() in names:
            raise ValueError(f"Duplicate squad member: {name}")
        names.add(name.casefold())
        counts[role] += 1
    return {"squad_size": len(roster), "role_counts": counts, "playing_xi_confirmed": False}
