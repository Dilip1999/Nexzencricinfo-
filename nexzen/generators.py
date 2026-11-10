"""Five pillar-specific brief generators. They structure supplied evidence; they never invent stats."""
from __future__ import annotations
from typing import Any
from .models import ContentBrief, PILLARS

HOOKS = {
    "stats": "The scorecard tells one story. The underlying numbers tell another.",
    "squads": "Does this squad have the balance to go all the way?",
    "records": "A remarkable cricket milestone — and the numbers behind it.",
    "battles": "Two players. One matchup. What does the evidence say?",
    "analyst": "Let's break down the tactical detail that could decide this match.",
}
CTAS = {
    "stats": "Which metric do you value most? Tell us below.",
    "squads": "Who would make your playing XI? Join the discussion.",
    "records": "Which cricket record deserves its own story next?",
    "battles": "Who has the edge, and in which conditions?",
    "analyst": "What tactical change would you make?",
}

def generate_brief(
    pillar: str, *, title: str, context: str, analysis: str, takeaway: str,
    claims: list[dict[str, Any]], sources: dict[str, dict[str, str]],
    format: str = "T20", competition: str = "", as_of: str = "",
    hook: str | None = None, cta: str | None = None,
    visual_concept: str = "Editorial motion-graphics with evidence-led data cards",
    metadata: dict[str, Any] | None = None,
) -> ContentBrief:
    """Create a draft from supplied evidence. Source IDs must resolve in the source map."""
    if pillar not in PILLARS:
        raise ValueError(f"pillar must be one of: {', '.join(PILLARS)}")
    if not title.strip() or not context.strip() or not analysis.strip() or not takeaway.strip():
        raise ValueError("title, context, analysis and takeaway are required.")
    if not claims or not sources:
        raise ValueError("At least one factual claim and one source are required.")
    merged_metadata = dict(metadata or {})
    merged_metadata.setdefault("visual_concept", visual_concept)
    merged_metadata.setdefault("brand_theme", "cricket-journal-editorial-luxury")
    raw = {
        "pillar": pillar, "title": title, "hook": hook or HOOKS[pillar],
        "context": context, "analysis": analysis, "takeaway": takeaway,
        "cta": cta or CTAS[pillar], "claims": claims, "sources": sources,
        "format": format, "competition": competition, "as_of": as_of,
        "status": "draft", "metadata": merged_metadata,
    }
    return ContentBrief.from_dict(raw)

def generate_stats_brief(**kwargs) -> ContentBrief:
    return generate_brief("stats", **kwargs)

def generate_squad_brief(**kwargs) -> ContentBrief:
    return generate_brief("squads", **kwargs)

def generate_record_brief(**kwargs) -> ContentBrief:
    return generate_brief("records", **kwargs)

def generate_battle_brief(**kwargs) -> ContentBrief:
    return generate_brief("battles", **kwargs)

def generate_analyst_brief(**kwargs) -> ContentBrief:
    return generate_brief("analyst", **kwargs)

GENERATORS = {
    "stats": generate_stats_brief,
    "squads": generate_squad_brief,
    "records": generate_record_brief,
    "battles": generate_battle_brief,
    "analyst": generate_analyst_brief,
}
