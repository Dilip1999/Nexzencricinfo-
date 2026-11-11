"""Editorial story selection: prioritize meaningful cricket stories, not every fixture."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

FULL_MEMBERS = (
    "Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland",
    "New Zealand", "Pakistan", "South Africa", "Sri Lanka", "West Indies", "Zimbabwe",
)
COUNTRY_ALIASES = {
    "afg":"Afghanistan", "aus":"Australia", "ban":"Bangladesh", "eng":"England",
    "ind":"India", "ire":"Ireland", "nz":"New Zealand", "pak":"Pakistan",
    "sa":"South Africa", "sl":"Sri Lanka", "wi":"West Indies", "zim":"Zimbabwe",
}
PRIORITY_COUNTRIES = ("India", "Pakistan", "England", "Australia")
PRIORITY_COMPETITIONS = ("ICC", "IPL", "World Cup", "Champions Trophy", "World Test Championship")
APPROVED_PILLARS = ("stats", "squads", "records", "battles", "analyst", "breaking")
MINIMUM_SCORE = 16
MAX_STORIES_PER_RUN = 3

@dataclass(frozen=True)
class StoryCandidate:
    id: str
    title: str
    country: str
    pillar: str
    event_type: str
    summary: str
    source_url: str
    source_name: str
    significance: int
    audience_interest: int
    analytical_value: int
    freshness: int
    evidence_quality: int
    unique_angle: bool = True
    match_has_story: bool = False
    competition: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StoryCandidate":
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def normalize_country(value: str) -> str | None:
    cleaned = " ".join(str(value or "").strip().split())
    if cleaned in FULL_MEMBERS:
        return cleaned
    return COUNTRY_ALIASES.get(cleaned.lower())

def score_story(candidate: StoryCandidate) -> dict[str, Any]:
    """Score five editorial dimensions (0–5 each); reject weak sourcing and fixture-only items."""
    dimensions = {
        "significance": candidate.significance,
        "audience_interest": candidate.audience_interest,
        "analytical_value": candidate.analytical_value,
        "freshness": candidate.freshness,
        "evidence_quality": candidate.evidence_quality,
    }
    invalid = [name for name, value in dimensions.items()
               if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5]
    reasons = []
    if invalid:
        reasons.append("Scores must be whole numbers from 0 to 5: " + ", ".join(invalid))
    if normalize_country(candidate.country) is None:
        reasons.append("Country is outside the configured ICC Full Member coverage.")
    if candidate.pillar not in APPROVED_PILLARS:
        reasons.append("Unsupported editorial pillar.")
    if not candidate.id.strip() or not candidate.title.strip() or not candidate.summary.strip():
        reasons.append("Candidate ID, title and story summary are required.")
    if not candidate.source_name.strip() or not candidate.source_url.startswith("https://"):
        reasons.append("A named HTTPS source is required.")
    if not candidate.unique_angle:
        reasons.append("No distinct editorial angle; avoid repetitive coverage.")
    if candidate.event_type == "ordinary_match" and not candidate.match_has_story:
        reasons.append("Ordinary match without a compelling story angle is excluded.")
    total = sum(value for value in dimensions.values() if isinstance(value, int) and not isinstance(value, bool))
    # A primary-country or flagship-event bonus is capped and never compensates for weak evidence.
    country = normalize_country(candidate.country)
    priority_bonus = 1 if country in PRIORITY_COUNTRIES else 0
    competition_bonus = 1 if any(term.lower() in candidate.competition.lower() for term in PRIORITY_COMPETITIONS) else 0
    score = min(25, total + priority_bonus + competition_bonus)
    if candidate.evidence_quality < 3:
        reasons.append("Evidence quality below minimum threshold.")
    if candidate.freshness < 2:
        reasons.append("Story is too stale for the current editorial queue.")
    selected = not reasons and score >= MINIMUM_SCORE
    if not selected and not reasons:
        reasons.append(f"Editorial score {score}/25 is below the {MINIMUM_SCORE}/25 threshold.")
    return {
        "id": candidate.id, "score": score, "base_score": total,
        "priority_bonus": priority_bonus, "competition_bonus": competition_bonus,
        "selected": selected, "reasons": reasons,
        "country": country, "pillar": candidate.pillar,
    }

def select_stories(candidates: list[StoryCandidate], *, limit: int = MAX_STORIES_PER_RUN) -> dict[str, Any]:
    """Return only high-scoring, distinct stories. Never select a match just because it was played."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    evaluated = [(candidate, score_story(candidate)) for candidate in candidates]
    seen = set()
    selected = []
    for candidate, result in sorted(evaluated, key=lambda pair: (-pair[1]["score"], pair[0].id)):
        if not result["selected"]:
            continue
        dedupe_key = (result["country"], candidate.pillar, candidate.title.casefold().strip())
        if dedupe_key in seen:
            result["selected"] = False
            result["reasons"].append("Duplicate story in this editorial batch.")
            continue
        seen.add(dedupe_key)
        selected.append({"candidate": candidate.to_dict(), "evaluation": result})
        if len(selected) >= limit:
            break
    return {
        "coverage": list(FULL_MEMBERS),
        "selection_policy": "high-signal stories only; ordinary fixtures are excluded without a distinct angle",
        "minimum_score": MINIMUM_SCORE,
        "selected": selected,
        "evaluated": [result for _, result in evaluated],
        "rejected_count": sum(1 for _, result in evaluated if not result["selected"]),
    }
