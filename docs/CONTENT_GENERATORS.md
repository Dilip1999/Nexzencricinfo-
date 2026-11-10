# Five cricket content generators — QA milestone 3

The package now exposes five pillar-specific functions through `nexzen.generators.GENERATORS`:

- `stats`: performance trends and statistical explainers
- `squads`: squad composition and role-balance stories
- `records`: records and milestones
- `battles`: player-v-player or batter-v-bowler comparisons
- `analyst`: tactical and match-intelligence explainers

Each function accepts a structured editorial context, factual claims and a source map. It creates a draft `ContentBrief` with a pillar-specific hook and CTA, consistent visual metadata and provenance references. The caller should run `validate_brief()` before creating a storyboard.

## Deliberate safety boundary

These functions do not fetch live data, generate statistics, infer a confirmed playing XI, or validate that a claim is true. They only structure evidence supplied by an upstream data provider/editor. Placeholder fixtures in tests are synthetic and are not publishable cricket content.

## Example

```python
from nexzen.generators import generate_stats_brief
from nexzen.quality import validate_brief
from nexzen.editorial import build_reel_script

brief = generate_stats_brief(
    title="A format-specific batting trend",
    context="Define the player, format, competition and date range.",
    analysis="Explain only what the verified data supports.",
    takeaway="State the narrow conclusion supported by the sample.",
    claims=[{"text": "Insert a verified scorecard fact.", "source_ids": ["scorecard"]}],
    sources={"scorecard": {"name": "Official scorecard", "url": "https://provider.example/scorecard"}},
    format="T20", competition="Competition name", as_of="YYYY-MM-DD",
)
result = validate_brief(brief)
if result.eligible:
    print(build_reel_script(brief))
```

The example URL and claim are placeholders; replace them with a real source and independently verified fact.
