"""Fetch one recent match and its scorecard; write a safe analysis-ready QA artifact."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import quote
from .providers.cricketdata import CricketDataClient, CricketDataError
from .scorecard_analysis import analyze_scorecard

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("qa-output"))
    args = parser.parse_args()
    client = CricketDataClient()
    if not client.configured:
        print("CRICKETDATA_API_KEY is not configured.")
        return 2
    try:
        listing = client.matches(limit=10)
        rows = listing.get("data")
        if not isinstance(rows, list) or not rows:
            print("No recent matches returned by the provider.")
            return 1
        selected = next((row for row in rows if row.get("match") and row.get("coverage") in (None, "full", "scorecard")), None)
        if selected is None:
            print("No recent match with a usable scorecard address was returned.")
            return 1
        match_id = str(selected["match"])
        raw_scorecard = client.scorecard(match_id)
        source_url = f"https://cricketdatabase.com/matches/{quote(match_id, safe='-')}"
        report = analyze_scorecard(raw_scorecard, source_url=source_url)
        report["match_listing_context"] = {
            "date": selected.get("date"), "format": selected.get("format"),
            "competition": selected.get("competition"), "coverage": selected.get("coverage"),
        }
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "sample-scorecard-analysis.json"
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print("PASS: fetched a recent match and normalized its scorecard.")
        print(f"Match address: {match_id}")
        print(f"Innings analyzed: {len(report['innings'])}")
        print(f"Artifact: {target.as_posix()}")
        print("No API key or raw authentication headers were logged.")
        return 0
    except CricketDataError:
        print("FAIL: provider rejected the request or returned an API error.")
        return 1
    except (ValueError, KeyError, TypeError):
        print("FAIL: provider response did not match the expected scorecard structure.")
        return 1
    except Exception as exc:
        print(f"FAIL: unexpected error ({type(exc).__name__}); details suppressed.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
