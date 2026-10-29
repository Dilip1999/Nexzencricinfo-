"""Generate a polished six-slide Top 5 cricket news carousel."""
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
SIZE = (1080, 1350)
NAVY = (7, 18, 40)
PANEL = (15, 39, 77)
TEAL = (45, 230, 190)
GOLD = (255, 204, 75)
WHITE = (248, 250, 255)
MUTED = (184, 205, 230)


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def fetch_articles() -> list[dict[str, str]]:
    feed = feedparser.parse(NEWS_FEED)
    items, seen = [], set()
    for entry in feed.entries:
        title = clean_text(str(entry.get("title", "")))
        url = str(entry.get("link", "")).strip()
        normalized = re.sub(r"\W+", " ", title.lower()).strip()
        if not title or not url or normalized in seen:
            continue
        seen.add(normalized)
        summary = clean_text(str(entry.get("summary", "")))
        if summary.lower().startswith(title.lower()):
            summary = summary[len(title):].strip(" -|:")
        items.append({"title": title, "url": url, "summary": summary[:320]})
        if len(items) == MAX_ARTICLES:
            break
    if not items:
        raise RuntimeError("No cricket articles returned by RSS feed.")
    return items


def font(size: int, bold: bool = False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def wrap(draw, text: str, f, width: int) -> list[str]:
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


def base_slide(slide_no: int, date: str):
    im = Image.new("RGB", SIZE, NAVY)
    d = ImageDraw.Draw(im)
    # Restrained editorial frame with diagonal accent blocks.
    d.rounded_rectangle((28, 28, 1052, 1322), radius=38, fill=PANEL, outline=TEAL, width=3)
    d.polygon([(770, 28), (1052, 28), (1052, 310)], fill=(20, 57, 101))
    d.text((70, 62), "NEXZENCRICINFO", font=font(31, True), fill=TEAL)
    d.text((70, 112), "CRICKET  /  NEWS  /  INSIGHT", font=font(18, True), fill=MUTED)
    d.line((70, 165, 1010, 165), fill=TEAL, width=3)
    d.text((70, 1260), "FOLLOW @NEXZENCRICINFO", font=font(19, True), fill=TEAL)
    d.text((880, 1258), f"{slide_no}/6  •  {date}", font=font(17, True), fill=MUTED)
    return im, d


def save_slide(im, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=93, optimize=True)


def create_carousel(articles: list[dict[str, str]], date: str, directory: Path) -> list[Path]:
    paths = []
    # Cover
    im, d = base_slide(1, date)
    d.text((72, 260), "THE DAILY", font=font(54, True), fill=WHITE)
    d.text((72, 330), "CRICKET", font=font(94, True), fill=GOLD)
    d.text((72, 435), "NEWS FIVE", font=font(94, True), fill=TEAL)
    d.text((76, 565), "5 stories. One swipe. Stay in the game.", font=font(28), fill=WHITE)
    d.rounded_rectangle((72, 660, 1008, 1105), radius=28, fill=(8, 25, 53), outline=(53, 91, 140), width=2)
    for i, article in enumerate(articles, 1):
        y = 700 + (i - 1) * 78
        d.ellipse((105, y, 155, y + 50), fill=TEAL)
        d.text((122, y + 8), str(i), font=font(24, True), fill=NAVY)
        lines = wrap(d, article["title"], font(22, True), 800)
        d.text((180, y + 3), lines[0][:95], font=font(22, True), fill=WHITE)
    d.text((78, 1150), "SWIPE TO CATCH UP  →", font=font(25, True), fill=GOLD)
    path = directory / "slide-1.jpg"
    save_slide(im, path)
    paths.append(path)

    # Individual story slides: readable headline and digest, no publisher URLs.
    for index, article in enumerate(articles, 1):
        im, d = base_slide(index + 1, date)
        d.rounded_rectangle((72, 220, 1008, 310), radius=20, fill=TEAL)
        d.text((105, 244), f"STORY {index:02d}  /  TOP 5 TODAY", font=font(27, True), fill=NAVY)
        d.text((78, 375), f"0{index}", font=font(112, True), fill=GOLD)
        title_lines = wrap(d, article["title"], font(47, True), 850)[:5]
        y = 520
        for line in title_lines:
            d.text((78, y), line, font=font(47, True), fill=WHITE)
            y += 65
        summary = article["summary"] or "A developing cricket story to keep on your radar."
        summary_lines = wrap(d, summary, font(28), 850)[:6]
        y = max(y + 35, 850)
        d.rounded_rectangle((72, y - 22, 1008, min(y + 390, 1190)), radius=25, fill=(8, 25, 53), outline=(53, 91, 140), width=2)
        for line in summary_lines:
            d.text((105, y + 18), line, font=font(28), fill=MUTED)
            y += 48
        d.text((78, 1160), "MORE CRICKET STORIES →  SWIPE", font=font(21, True), fill=GOLD)
        path = directory / f"slide-{index + 1}.jpg"
        save_slide(im, path)
        paths.append(path)
    return paths


def main():
    today = datetime.now(IST).date().isoformat()
    articles = fetch_articles()
    caption = (
        f"🏏 TOP 5 CRICKET NEWS | {today}\n\n"
        + "\n\n".join(
            f"{i}. {a['title']}" + (f"\n{a['summary']}" if a["summary"] else "")
            for i, a in enumerate(articles, 1)
        )
        + "\n\nWhich story caught your attention? Tell us in the comments! 💬"
        "\n❤️ Save this carousel and share it with a cricket fan."
        "\n\n#Cricket #CricketNews #IndianCricket #ICC #NexZenCricInfo"
        "\n\nWhere Next Gen Cricket Begins 🏏"
    )
    Path("drafts").mkdir(exist_ok=True)
    image_dir = Path("images") / today
    image_dir.mkdir(parents=True, exist_ok=True)
    paths = create_carousel(articles, today, image_dir)
    draft = (
        f"# NexZenCricInfo — Top 5 Cricket News ({today})\n\n{caption}\n\n"
        "## Source notes (not included in Instagram caption)\n\n"
        + "\n".join(f"{i}. {a['title']} — {a['url']}" for i, a in enumerate(articles, 1))
        + f"\n\nGenerated at {datetime.now(timezone.utc).isoformat()} (UTC)\n"
    )
    Path("drafts", f"{today}.md").write_text(draft, encoding="utf-8")
    print(f"Created a {len(paths)}-slide cricket news carousel for {today}")


if __name__ == "__main__":
    main()
