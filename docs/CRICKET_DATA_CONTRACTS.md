# Cricket data intelligence — QA milestone 2

This milestone adds provider-neutral data contracts and deterministic metric calculations. It does not yet fetch live cricket data.

## Metrics
- Batting average = runs / dismissals; undefined when dismissals are zero.
- Strike rate = 100 × runs / balls faced; undefined when balls faced are zero.
- Bowling economy = runs conceded × 6 / legal balls; undefined when no legal balls were bowled.
- Bowling average = runs conceded / wickets; undefined when no wickets were taken.
- Overs are represented as completed overs plus remaining legal balls (for example, 47 balls = 7.5 overs), not as a decimal fraction.

## Data integrity
Every production dataset must carry provider/source, retrieval time, format, competition, date range, and sample size. Player comparisons must use aligned contexts. Squad role counts are descriptive only; this module never declares a playing XI confirmed.

## Next
Select and implement a licensed data provider adapter after reviewing its current coverage, attribution rules, request limits and cost. Add provider contract tests and a small, source-cited fixture before enabling any generated cricket claims.
