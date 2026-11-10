"""Validate a JSON content brief and render a storyboard only when eligible."""
import argparse
import json
from pathlib import Path
from .models import ContentBrief
from .quality import validate_brief
from .editorial import build_reel_script

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("brief", type=Path)
    parser.add_argument("--out", type=Path, default=Path("qa-output"))
    args = parser.parse_args()
    brief = ContentBrief.from_dict(json.loads(args.brief.read_text(encoding="utf-8")))
    result = validate_brief(brief)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "quality-report.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    if result.eligible:
        (args.out / "reel-storyboard.md").write_text(build_reel_script(brief), encoding="utf-8")
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.eligible else 2

if __name__ == "__main__":
    raise SystemExit(main())
