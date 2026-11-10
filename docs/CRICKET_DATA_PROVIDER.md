# Cricket data provider adapter

## Provider evaluated: CricketData.org / CricAPI

Official docs currently describe:
- Matches list: `GET /v1/matches`
- Series list/search: `GET /v1/series`
- Player search: `GET /v1/players`
- Scorecard: `GET /v1/match_scorecard?id=...`
- Squad: `GET /v1/match_squad?id=...`

The provider documents a lifetime-free tier with 100 API hits/day and paid tiers beginning at $5.99/month. It says the free tier can have data a few minutes behind real time. Fantasy scorecard/squad endpoints may have paid-plan restrictions or trial-mode limitations. Verify current account entitlement, tournament coverage, data rights and usage terms in the provider console before production use.

References:
- https://cricketdata.org/pricing/
- https://cricketdata.org/python-code-samples/
- https://cricketdata.org/how-to-use-fantasy-cricket-api.aspx

## Implementation in this branch

`nexzen/providers/cricketdata.py` provides a small client for matches, series, player search, scorecards and squads. It reads `CRICKETDATA_API_KEY` from the environment and uses the provider's documented API-key query parameter. Since the provider requires query-string authentication, never log full request URLs or expose request objects in logs.

## Configure locally / GitHub Actions

Add repository secret `CRICKETDATA_API_KEY` only after creating an account and reviewing terms. Do not add the key to source code, JSON fixtures, workflow YAML or commit history.

## Current limitation

This is a transport adapter, not a normalized data pipeline. Provider response schemas and actual entitlement must be verified using the user's own key. No live calls or Instagram publishing are performed by the QA test suite. The current free tier is a candidate for prototyping, not a guarantee of historical-statistics coverage.
