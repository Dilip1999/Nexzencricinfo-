# NexZenCricInfo 2.0 — QA implementation

## Branch safety
All work is isolated to `QA`. Production `main` is not modified. Do not merge until the owner reviews sample Reels and explicitly approves a pull request.

## Content pillars
- `stats`: performance statistics and trends
- `squads`: squad depth, combinations and playing-XI analysis
- `records`: historical records and milestones
- `battles`: player-versus-player and batter-versus-bowler comparisons
- `analyst`: match tactics and evidence-led match intelligence

News and breaking coverage remain part of the existing editorial mix.

## Delivered in this QA milestone
- Typed content brief and claim/source provenance model.
- Fail-closed provenance checks and weighted quality score.
- Pillar-aware 25–40 second Reel storyboard.
- CLI writes a quality report and only writes a storyboard after the quality gate passes.
- Unit tests for missing sources, unsupported HTTP sources, missing claim references and invalid pillars.
- GitHub Actions QA workflow; it tests code only and does not publish to Instagram.

## Quality score
Source reliability 30%, relevance 20%, hook/storytelling 20%, original insight 15%, visual suitability 10%, brand consistency 5%. Scores 85+ are eligible for final human review; 70–84 need improvement; below 70 should be regenerated. Missing provenance always fails closed.

The gate validates source metadata and claim-to-source references. It does not independently prove that a source is authoritative or that a claim matches the source. Human verification and provider-specific adapters are still required before publication.

## Run locally
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m nexzen.cli examples/content-brief.template.json
```
The template intentionally contains placeholder source information and should fail closed.

## Next QA increments
1. Add provider adapters after checking API coverage, licensing, limits and cost.
2. Add structured player, team, match, scorecard and historical-record models.
3. Implement statistic calculations with format/competition/period context and tests.
4. Add five pillar-specific brief generators and editorial selection/deduplication.
5. Build the motion-graphics renderer and produce three reviewed sample Reels.
6. Test publishing on QA with publishing disabled by default.
7. Update production workflow only through a reviewed QA-to-main pull request.

## Not changed
Existing production scripts, scheduled workflow, Instagram publisher, publication history and `main` remain untouched in this milestone.
