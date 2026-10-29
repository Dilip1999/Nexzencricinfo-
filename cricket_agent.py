"""Create a concise top-five cricket news Instagram post from RSS."""
from __future__ import annotations
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import feedparser
from PIL import Image, ImageDraw, ImageFont

IST = ZoneInfo("Asia/Kolkata")
NEWS_FEED = "https://news.google.com/rss/search?q=cricket+(India+OR+IPL+OR+ICC+OR+Test+OR+ODI+OR+T20)&hl=en-IN&gl=IN&ceid=IN:en"
MAX_ARTICLES = 5

def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()

def fetch_articles() -> list[dict[str, str]]:
    feed = feedparser.parse(NEWS_FEED)
    items, seen = [], set()
    for entry in feed.entries:
        title = clean_text(str(entry.get("title", "")))
        url = str(entry.get("link", "")).strip()
        # Keep distinct headlines and avoid URL/source boilerplate in the post text.
        normalized = re.sub(r"\W+", " ", title.lower()).strip()
        if not title or not url or normalized in seen:
            continue
        seen.add(normalized)
        summary = clean_text(str(entry.get("summary", "")))
        # RSS summaries often append publisher text after the headline.
        if summary.lower().startswith(title.lower()):
            summary = summary[len(title):].strip(" -|:")
        items.append({"title": title, "url": url, "summary": summary[:260]})
        if len(items) >= MAX_ARTICLES:
            break
    if not items:
        raise RuntimeError("No cricket articles returned by RSS feed.")
    return items

def font(size: int, bold: bool = False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        return ImageFont.truetype(p, size)
    except OSError:
        return ImageFont.load_default()

def wrap(draw, text, f, width):
    result, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] <= width:
            line = candidate
        else:
            if line:
                result.append(line)
            line = word
    if line:
        result.append(line)
    return result

def create_image(articles: list[dict[str, str]], date: str, path: Path):
    # Template-created branded editorial graphic; no AI-generated player likenesses.
    im = Image.new("RGB", (1080, 1350), (7, 18, 40))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((35, 35, 1045, 1315), radius=36, fill=(13, 35, 70), outline=(35, 220, 180), width=4)
    d.text((75, 75), "NEXZENCRICINFO", font=font(38, True), fill=(45, 230, 190))
    d.text((75, 130), "CRICKET • NEWS • INSIGHT", font=font(22, True), fill=(190, 215, 240))
    d.line((75, 185, 1005, 185), fill=(45, 230, 190), width=3)
    d.text((75, 220), "TOP 5 CRICKET NEWS", font=font(46, True), fill=(255, 204, 75))
    d.text((75, 280), date, font=font(23), fill=(190, 215, 240))
    y = 335
    for idx, article in enumerate(articles, 1):
        d.rounded_rectangle((70, y, 1010, y + 155), radius=20, fill=(20, 49, 91), outline=(50, 90, 135), width=2)
        d.ellipse((92, y + 38, 158, y + 104), fill=(45, 230, 190))
        d.text((112, y + 50), str(idx), font=font(32, True), fill=(7, 18, 40))
        lines = wrap(d, article["title"], font(25, True), 800)[:3]
        ty = y + 28
        for line in lines:
            d.text((185, ty), line, font=font(25, True), fill="white")
            ty += 36
        y += 170
    d.rounded_rectangle((75, 1210, 1005, 1270), radius=18, fill=(45, 230, 190))
    d.text((105, 1227), "Follow @nexzencricinfo for more cricket updates", font=font(23, True), fill=(7, 18, 40))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=92, optimize=True)

def main():
    today = datetime.now(IST).date().isoformat()
    articles = fetch_articles()
    # URLs are kept only in the private draft's source notes, never in the Instagram caption.
    caption = (
        f"🏏 TOP 5 CRICKET NEWS | {today}\n\n"
        + "\n".join(f"{i}. {a['title']}" + (f"\n   {a['summary']}" if a["summary"] else "") for i, a in enumerate(articles, 1))
        + "\n\nWhich story caught your attention? Tell us in the comments! 💬\n\n"
        "#Cricket #CricketNews #IndianCricket #ICC #NexZenCricInfo\n\n"
        "Where Next Gen Cricket Begins 🏏"
    )
    Path("drafts").mkdir(exist_ok=True)
    Path("images").mkdir(exist_ok=True)
    draft = (
        f"# NexZenCricInfo — Top 5 Cricket News ({today})\n\n{caption}\n\n"
        "## Source notes (not included in Instagram caption)\n\n"
        + "\n".join(f"{i}. {a['title']} — {a['url']}" for i, a in enumerate(articles, 1))
        + f"\n\nGenerated at {datetime.now(timezone.utc).isoformat()} (UTC)\n"
    )
    Path("drafts", f"{today}.md").write_text(draft, encoding="utf-8")
    create_image(articles, today, Path("images", f"{today}.jpg"))
    print(f"Top {len(articles)} cricket stories, caption, and graphic created for {today}")

if __name__ == "__main__":
    main()
