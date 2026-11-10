"""Pillar-aware short-form cricket storytelling."""
from .models import ContentBrief

PILLAR_LABELS = {"stats":"STATS & ANALYTICS", "squads":"SQUAD ANALYSIS", "records":"RECORDS & MILESTONES", "battles":"PLAYER BATTLE", "analyst":"MATCH INTELLIGENCE"}

def build_reel_script(brief: ContentBrief) -> str:
    """Build a storyboard draft; callers must run the quality gate first."""
    claims = "\n".join(f"• {claim.text}" for claim in brief.claims)
    sources = "\n".join(f"• {source.name}: {source.url}" for source in brief.sources.values())
    return f"""# {brief.title}

**Pillar:** {PILLAR_LABELS.get(brief.pillar, brief.pillar)}  
**Format:** {brief.format}  
**Competition:** {brief.competition or 'Not specified'}  
**Data as of:** {brief.as_of or 'Not specified'}

## Reel storyboard (25–40 seconds)

| Time | Scene | Voiceover / on-screen copy |
|---|---|---|
| 0–3s | Hook | {brief.hook} |
| 3–8s | Context | {brief.context} |
| 8–18s | Evidence | {claims} |
| 18–28s | Analysis | {brief.analysis} |
| 28–35s | Takeaway | {brief.takeaway} |
| 35–40s | CTA | {brief.cta} |

## Sources for editorial review
{sources}

## Production direction
- Visual identity: ivory, burgundy, charcoal and subtle gold.
- Style: premium cricket-journal editorial with clear mobile typography.
- Use animated charts only when supplied data supports them.
- Label predictions and probable XIs; never present them as confirmed facts.
- Draft storyboard only; this is not an approved or published Reel.
"""
