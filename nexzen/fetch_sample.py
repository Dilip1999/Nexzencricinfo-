"""Fetch one recent match and its scorecard; write a safe QA artifact."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from urllib.parse import quote
from .providers.cricketdata import CricketDataClient, CricketDataError
from .scorecard_analysis import analyze_scorecard
from .quality_gate import validate_analysis_report

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("qa-output"))
    args=parser.parse_args()
    client=CricketDataClient()
    if not client.configured:
        print("CRICKETDATA_API_KEY is not configured."); return 2
    try:
        listing=client.matches(limit=10); rows=listing.get("data")
        if not isinstance(rows,list) or not rows:
            print("No recent matches returned by provider."); return 1
        selected=next((row for row in rows if row.get("match") and row.get("coverage") in (None,"full","scorecard")),None)
        if selected is None:
            print("No recent match with a usable scorecard address was returned."); return 1
        match_id=str(selected["match"])
        raw=client.scorecard(match_id)
        report=analyze_scorecard(raw,source_url=f"https://cricketdatabase.com/matches/{quote(match_id,safe='-')}")
        report["match_listing_context"]={"date":selected.get("date"),"format":selected.get("format"),
            "competition":selected.get("competition"),"coverage":selected.get("coverage")}
        report["quality_gate"]=validate_analysis_report(report)
        args.out.mkdir(parents=True,exist_ok=True)
        target=args.out/"sample-scorecard-analysis.json"
        target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        print(f"Quality gate: {report['quality_gate']['status']}")
        print(f"Warnings: {len(report['quality_gate']['warnings'])}; errors: {len(report['quality_gate']['errors'])}")
        print(f"Artifact: {target.as_posix()}")
        if report["quality_gate"]["status"] == "blocked":
            print("FAIL: scorecard integrity errors block editorial use."); return 1
        if report["quality_gate"]["status"] == "needs_human_review":
            print("PASS WITH REVIEW: artifact created but not eligible for publication.")
        else:
            print("PASS: scorecard passed deterministic integrity checks.")
        print("No API key or authentication headers were logged.")
        return 0
    except CricketDataError:
        print("FAIL: provider rejected the request or returned an API error."); return 1
    except (ValueError,KeyError,TypeError):
        print("FAIL: provider response did not match expected scorecard structure."); return 1
    except Exception as exc:
        print(f"FAIL: unexpected error ({type(exc).__name__}); details suppressed."); return 1

if __name__=="__main__": raise SystemExit(main())
