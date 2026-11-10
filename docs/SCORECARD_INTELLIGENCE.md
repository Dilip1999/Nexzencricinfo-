# Scorecard intelligence pipeline — QA milestone 5

## Flow
1. Request up to 10 recent matches using the free-plan `GET /v1/matches?limit=10` endpoint.
2. Select the first match that has an address and full/scorecard coverage.
3. Fetch `GET /v1/matches/{match}/scorecard`.
4. Normalize innings, batting cards, bowling cards, top scorers and bowling figures.
5. Preserve the match address, date/format/competition context and provider source URL.
6. Upload a JSON artifact for human review. No Reel or Instagram publishing occurs.

## Derived metrics
- Batter strike rate = runs / balls × 100.
- Bowler economy = runs conceded × 6 / legal balls.
- Cricket overs notation is parsed as completed overs plus remaining balls; 3.4 overs is 22 legal balls, not 3.4 decimal overs.

## Boundaries
This is a single-match scorecard analysis, not career stats or historical records. Career stats require `/players/{player}/stats`; records use `/records`. The free key includes scorecards from the last 30 days and recent match listings, but not live matches. A scorecard is not proof of the current or confirmed squad/playing XI.

All outputs are data-ready for human review only. They are not approved editorial claims and cannot be auto-published.

## Run
```bash
python -m unittest tests.test_scorecard_analysis -v
CRICKETDATA_API_KEY=... python -m nexzen.fetch_sample --out qa-output
```
Never put the key in source code, command history shared publicly, logs or artifacts.
