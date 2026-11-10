"""Minimal, safe Cricket Database QA smoke test. Never prints credentials or raw API data."""
from __future__ import annotations
import json
import os
import sys
from nexzen.providers.cricketdata import CricketDataClient, CricketDataError

def main() -> int:
    client = CricketDataClient()
    if not client.configured:
        print("FAIL: CRICKETDATA_API_KEY is not available to this workflow.")
        return 2
    try:
        payload = client.matches()
    except CricketDataError as exc:
        # Avoid provider-supplied exception strings, which may contain sensitive data.
        print("FAIL: Cricket Database request was rejected or returned invalid data.")
        print(f"Error category: {type(exc).__name__}")
        return 1
    except Exception as exc:
        print(f"FAIL: request failed ({type(exc).__name__}); no credentials or URLs printed.")
        return 1
    data = payload.get("data")
    if not isinstance(data, (list, dict)):
        print("FAIL: unexpected data field type.")
        return 1
    count = len(data)
    print("PASS: Cricket Database authentication/request and JSON response succeeded.")
    print(f"Response data type: {type(data).__name__}")
    print(f"Top-level data entries: {count}")
    print("No match names, raw response payloads or credentials were logged.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
