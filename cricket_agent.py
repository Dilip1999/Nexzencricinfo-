"""Create a template-based cricket news Instagram draft without paid AI APIs."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

IST = ZoneInfo("Asia/Kolkata")
OUTPUT_DIR = Path("drafts")
NEWS_FEED = (
    "https://news.google.com/rss/search?q="
    "cricket+(India+OR+IPL+OR+ICC+OR+Test+OR+ODI+OR+T20)&hl=en-IN&gl=IN&ceid=IN:en"
)
MAX_ARTICLES = 10


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_articles() -> list[dict[str, str]]:
    feed = feedparser.parse(NEWS_FEED)
    articles: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for entry in feed.entries:
        title = clean_text(str(entry.get("title", "")))
        url = str(entry.get("link", "")).strip()
        summary = clean_text(str(entry.get("summary", "")))
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
    # Template only: no AI API call and no invented details.
    selected = articles[0]
    summary = selected["summary"] or "Follow the linked report for available details."
    return (
        f"🏏 CRICKET UPDATE | {today}\n\n"
        f"{selected['title']}\n\n"
        f"{summary}\n\n"
        "What do you think about this development? Share your thoughts below!\n\n"
        "#Cricket #CricketNews #IndianCricket #ICC #IPL #NexZenCricInfo\n\n"
        f"Source: {selected['url']}\n\n"
        "Where Next Gen Cricket Begins"
    )


def main() -> int:
    if os.getenv("PUBLISH_TO_INSTAGRAM", "false").lower() == "true":
        print("Safety stop: Instagram publishing is not implemented in this draft-only version.", file=sys.stderr)
        return 2

    today = datetime.now(IST).date().isoformat()
    articles = fetch_articles()
    caption = generate_caption(articles, today)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{today}.md"
    lines = [
        f"# NexZenCricInfo — Cricket Post Draft ({today})",
        "",
        "> Template-generated draft; verify the linked report and facts before publishing.",
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
