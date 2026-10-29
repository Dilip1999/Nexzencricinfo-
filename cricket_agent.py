"""Generate an engaging six-slide Top 5 cricket news carousel."""
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
NAVY = (5, 14, 32)
PANEL = (12, 31, 61)
BLUE = (20, 89, 175)
TEAL = (40, 235, 190)
ORANGE = (255, 139, 48)
GOLD = (255, 205, 75)
WHITE = (250, 251, 255)
MUTED = (190, 208, 233)


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def clean_summary(summary: str, title: str) -> str:
    summary = clean_text(summary)
    # Google News RSS commonly repeats the title before the publisher.
    if summary.lower().startswith(title.lower()):
        summary = summary[len(title):].strip(" -|:—")
    summary = re.sub(r"\s+[—|]\s+[^—|]{2,80}$", "", summary).strip()
    if summary.lower() == title.lower():
        return ""
    return summary[:300]


def story_key(title: str) -> str:
    return re.sub(r"\\W+", " ", clean_text(title).lower()).strip()


def fetch_articles() -> list[dict[str, str]]:
    feed = feedparser.parse(NEWS_FEED)
    history_path = Path("content_history.json")
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"stories": []}
    previously_used = {story_key(str(item.get("title", ""))) for item in history.get("stories", [])}
    items, seen = [], set()
    for entry in feed.entries:
        title = clean_text(str(entry.get("title", "")))
        url = str(entry.get("link", "")).strip()
        key = story_key(title)
        if not title or not url or key in seen or key in previously_used:
            continue
        seen.add(key)
        summary = clean_summary(str(entry.get("summary", "")), title)
        items.append({"title": title, "url": url, "summary": summary})
        if len(items) == MAX_ARTICLES:
            break
    if not items:
        raise RuntimeError("No fresh cricket stories found after excluding previously published stories.")
    print(f"Selected {len(items)} fresh stories (history excludes {len(previously_used)} prior stories).")
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


def gradient_background():
    im = Image.new("RGB", SIZE, NAVY)
    pix = im.load()
    for y in range(SIZE[1]):
        blend = y / SIZE[1]
        color = tuple(int(NAVY[i] * (1 - blend) + PANEL[i] * blend) for i in range(3))
        for x in range(SIZE[0]):
            pix[x, y] = color
    return im


def base_slide(slide_no: int, date: str):
    im = gradient_background()
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((22, 22, 1058, 1328), radius=40, outline=TEAL, width=3)
    # Graphic corner accents create a sharper editorial/sports identity.
    d.polygon([(720, 24), (1056, 24), (1056, 270)], fill=(15, 48, 91))
    d.polygon([(22, 950), (22, 1326), (270, 1326)], fill=(8, 25, 50))
    d.text((66, 58), "NEXZENCRICINFO", font=font(31, True), fill=TEAL)
    d.text((68, 108), "CRICKET  /  NEWS  /  INSIGHT", font=font(18, True), fill=MUTED)
    d.line((68, 160, 1012, 160), fill=TEAL, width=3)
    d.text((68, 1263), "FOLLOW @NEXZENCRICINFO", font=font(19, True), fill=TEAL)
    d.text((855, 1261), f"{slide_no}/6  •  {date}", font=font(17, True), fill=MUTED)
    return im, d


def save_slide(im, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=95, optimize=True, subsampling=0)


def create_carousel(articles: list[dict[str, str]], date: str, directory: Path) -> list[Path]:
    paths = []
    # Cover slide with stronger hierarchy and a compact story rundown.
    im, d = base_slide(1, date)
    d.rounded_rectangle((68, 210, 1012, 1150), radius=32, fill=(7, 23, 48), outline=(42, 87, 145), width=2)
    d.text((100, 260), "YOUR DAILY", font=font(48, True), fill=WHITE)
    d.text((95, 325), "CRICKET", font=font(100, True), fill=GOLD)
    d.text((95, 430), "NEWS FIVE", font=font(92, True), fill=TEAL)
    d.text((102, 555), "The 5 stories cricket fans need today.", font=font(27), fill=WHITE)
    d.rounded_rectangle((100, 635, 980, 1055), radius=25, fill=(10, 31, 63), outline=(48, 90, 145), width=2)
    for i, article in enumerate(articles, 1):
        y = 675 + (i - 1) * 76
        d.ellipse((130, y, 180, y + 50), fill=TEAL)
        d.text((146, y + 8), str(i), font=font(24, True), fill=NAVY)
        lines = wrap(d, article["title"], font(21, True), 735)
        d.text((205, y + 5), lines[0][:90], font=font(21, True), fill=WHITE)
    d.text((105, 1090), "SWIPE  →  GET THE FULL STORY", font=font(24, True), fill=ORANGE)
    path = directory / "slide-1.jpg"
    save_slide(im, path)
    paths.append(path)

    for index, article in enumerate(articles, 1):
        im, d = base_slide(index + 1, date)
        d.rounded_rectangle((68, 205, 1012, 310), radius=22, fill=TEAL)
        d.text((100, 238), f"TOP 5 TODAY   •   STORY {index:02d}", font=font(27, True), fill=NAVY)
        d.text((72, 350), f"0{index}", font=font(110, True), fill=ORANGE)
        # Headline size adapts to its length to avoid clipping.
        headline_size = 48 if len(article["title"]) < 78 else 39
        title_lines = wrap(d, article["title"], font(headline_size, True), 850)[:5]
        y = 500
        for line in title_lines:
            d.text((78, y), line, font=font(headline_size, True), fill=WHITE)
            y += headline_size + 18
        summary = article["summary"] or "The latest development—follow the story as it unfolds."
        summary_lines = wrap(d, summary, font(28), 820)[:5]
        panel_top = max(y + 28, 820)
        panel_bottom = min(panel_top + 330, 1170)
        d.rounded_rectangle((72, panel_top, 1008, panel_bottom), radius=26, fill=(7, 24, 49), outline=(45, 93, 151), width=2)
        d.text((105, panel_top + 28), "THE KEY UPDATE", font=font(21, True), fill=TEAL)
        sy = panel_top + 75
        for line in summary_lines:
            if sy + 38 > panel_bottom - 20:
                break
            d.text((105, sy), line, font=font(27), fill=MUTED)
            sy += 45
        d.text((78, 1190), "SWIPE FOR MORE  •  SHARE WITH A CRICKET FAN", font=font(19, True), fill=GOLD)
        path = directory / f"slide-{index + 1}.jpg"
        save_slide(im, path)
        paths.append(path)
    return paths


def build_caption(articles: list[dict[str, str]], date: str) -> str:
    # A curiosity hook plus conversational prompt, save/share cues and targeted tags.
    story_lines = []
    for i, article in enumerate(articles, 1):
        title = article["title"].strip()
        summary = article["summary"].strip()
        story_lines.append(f"{i}️⃣ {title}" + (f"\n{summary}" if summary and summary.lower() not in title.lower() else ""))
    hashtags = (
        "#Cricket #CricketNews #CricketUpdates #IndianCricket #TeamIndia "
        "#ICC #CricketWorld #CricketFans #CricketLovers #SportsNews "
        "#CricketReels #CricketHighlights #DailyCricket #NexZenCricInfo #NZC"
    )
    return (
        f"🚨 CRICKET FANS, HERE'S YOUR DAILY UPDATE! 🏏\n"
        f"Five stories making waves in cricket today ({date}) — which one matters most? 👀\n\n"
        + "\n\n".join(story_lines)
        + "\n\n💬 YOUR TAKE: Which story surprised you the most? Drop your opinion below."
        "\n📌 Save this carousel so you’re caught up."
        "\n🔁 Share it with the cricket fan who needs these updates."
        "\n\n"
        + hashtags
        + "\n\nWhere Next Gen Cricket Begins 🏏"
    )


def main():
    today = datetime.now(IST).date().isoformat()
    articles = fetch_articles()
    caption = build_caption(articles, today)
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
    print(f"Created a {len(paths)}-slide engaging cricket carousel for {today}")


if __name__ == "__main__":
    main()
