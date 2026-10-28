"""Generate a sourced daily cricket Instagram caption draft. This script does not publish."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
from openai import OpenAI

IST = ZoneInfo("Asia/Kolkata")
OUTPUT_DIR = Path("drafts")
MODEL = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4.1-mini"
NEWS_FEED = (
    "https://news.google.com/rss/search?q="
    "cricket+(India+OR+IPL+OR+ICC+OR+Test+OR+ODI+OR+T20)&hl=en-IN&gl=IN&ceid=IN:en"
)
MAX_ARTICLES = 10


def fetch_articles() -> list[dict[str, str]]:
    feed = feedparser.parse(NEWS_FEED)
    articles: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for entry in feed.entries:
        title = re.sub(r"\s+", " ", str(entry.get("title", ""))).strip()
        url = str(entry.get("link", "")).strip()
        summary = re.sub(r"<[^>]+>", " ", str(entry.get("summary", "")))
        summary = re.sub(r"\s+", " ", summary).strip()
        if not title or not url or url in seen_urls:
            continue
        seen_urls.add(url)
        articles.append({"title": title, "url": url, "summary": summary[:500]})
        if len(articles) >= MAX_ARTICLES:
            break

    if not articles:
        raise RuntimeError("The news feed returned no articles. Try again later.")
    return articles


def generate_caption(articles: list[dict[str, str]], today: str) -> str:
    client = OpenAI()
    sources = "\n".join(
        f'{i}. Title: {a["title"]}\n   Summary: {a["summary"]}\n   URL: {a["url"]}'
        for i, a in enumerate(articles, start=1)
    )
    instructions = f"""
You are the cricket editor for NexZenCricInfo, whose tagline is "Where Next Gen Cricket Begins".
Create ONE Instagram feed-post draft in clear, natural English for {today}.

Use only facts supported by the source headlines/summaries below. Do not invent scores,
quotes, injuries, selections, dates, or outcomes. If details are uncertain, use cautious
wording or omit them. Select the most important current cricket story; prioritize
international cricket, ICC events, and IPL. Make the caption engaging but not clickbait.
Structure:
- A short headline with 1-2 relevant emojis
- 2-4 concise sentences explaining the news and why it matters
- A short question to encourage genuine comments
- 5-8 relevant hashtags, including #NexZenCricInfo
- A final "Sources:" section with 1-3 exact source URLs used
Do not claim this post has been published. Do not include unsupported information.
Return only the finished caption draft.

News items:
{sources}
"""
    response = client.responses.create(model=MODEL, input=instructions)
    caption = response.output_text.strip()
    if not caption:
        raise RuntimeError("The AI returned an empty caption.")
    return caption


def main() -> int:
    if os.getenv("PUBLISH_TO_INSTAGRAM", "false").lower() == "true":
        print("Safety stop: Instagram publishing is not implemented in this draft-only version.", file=sys.stderr)
        return 2

    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY. Add it as a GitHub Actions secret or to a local .env file.", file=sys.stderr)
        return 2

    today = datetime.now(IST).date().isoformat()
    articles = fetch_articles()
    caption = generate_caption(articles, today)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{today}.md"
    lines = [
        f"# NexZenCricInfo — Cricket Post Draft ({today})",
        "",
        "> Draft only — review facts, links, and wording before publishing.",
        "",
        caption,
        "",
        "## Articles collected",
        "",
    ]
    lines.extend(f'- [{a["title"]}]({a["url"]})' for a in articles)
    lines.extend(["", "---", f"Generated at {datetime.now(timezone.utc).isoformat()} (UTC)", ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Draft created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
