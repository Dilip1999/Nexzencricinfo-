# Cricket Database provider integration

Provider: https://cricketdatabase.com  
API root: https://api.cricketdatabase.com/v1  
Authentication: `Authorization: Bearer <key>`  
Secret: `CRICKETDATA_API_KEY`

The adapter is specifically for Cricket Database, not Cricapi / CricketData.org. It supports documented endpoints:
- `GET /matches`
- `GET /results/yesterday`
- `GET /matches/{match}`
- `GET /matches/{match}/scorecard`
- `GET /players/{player}/stats`
- `GET /search?q=...`
- `GET /live` (paid plans only; Free key does not include live matches)

## Free-plan constraints
The provider documentation currently states 50 successful calls/day and full recent results/scorecards for the last 30 days, with samples for older archive data. Live matches are not included on Free; Match Week, Pro and Analyst Pro include live access. Do not assume that an endpoint returning a sample represents full archive coverage.

## QA smoke test
Run the mocked contract tests with:
```bash
python -m unittest tests.test_cricketdata_client -v
```

The GitHub Actions QA workflow must inject `CRICKETDATA_API_KEY` from repository secrets only into a manually dispatched or QA-branch job. Never print the key, request headers, or full request URLs. Do not invoke paid-only endpoints as part of the free-plan smoke test.

Documentation: https://cricketdatabase.com/documentation
