"""Generate an engaging six-slide Top 5 cricket news carousel."""
from __future__ import annotations

import html
import json
import os
import re
from io import BytesIO
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
from opencricket_client import fetch_matches, match_to_article
from PIL import Image, ImageDraw, ImageFont

IST = ZoneInfo("Asia/Kolkata")
NEWS_FEED = "https://news.google.com/rss/search?q=cricket+(India+OR+IPL+OR+ICC+OR+Test+OR+ODI+OR+T20)&hl=en-IN&gl=IN&ceid=IN:en"
MAX_ARTICLES = 5
SIZE = (1080, 1350)
NAVY = (35, 31, 32)       # Editorial charcoal
PANEL = (250, 246, 239)   # Light editorial ivory
BLUE = (105, 24, 42)      # Deep burgundy
TEAL = (105, 24, 42)      # Burgundy brand accent
ORANGE = (183, 145, 82)   # Restrained editorial gold
GOLD = (183, 145, 82)     # Restrained editorial gold
WHITE = (250, 246, 239)   # Ivory for dark panels only
MUTED = (103, 91, 83)     # Readable warm grey


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
    return re.sub(r"\W+", " ", clean_text(title).lower()).strip()


def fetch_articles() -> list[dict[str, str]]:
    """Combine fresh OpenCricket match data with Google News RSS."""
    history_path = Path("content_history.json")
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"stories": []}
    previously_used = {story_key(str(item.get("title", ""))) for item in history.get("stories", [])}
    items, seen = [], set()
    try:
        for match in fetch_matches():
            article = match_to_article(match)
            if not article:
                continue
            key = story_key(article["title"])
            if key and key not in previously_used and key not in seen:
                seen.add(key)
                items.append(article)
                if len(items) >= MAX_ARTICLES:
                    break
    except Exception as exc:
        print(f"OpenCricket API unavailable; using RSS fallback ({type(exc).__name__}).")
    feed = feedparser.parse(NEWS_FEED)
    for entry in feed.entries:
        title = clean_text(str(entry.get("title", "")))
        url = str(entry.get("link", "")).strip()
        key = story_key(title)
        if not title or not url or key in seen or key in previously_used:
            continue
        seen.add(key)
        items.append({"title": title, "url": url,
                      "summary": clean_summary(str(entry.get("summary", "")), title),
                      "source": "Google News RSS"})
        if len(items) >= MAX_ARTICLES:
            break
    if not items:
        raise RuntimeError("No fresh cricket stories found from OpenCricket API or RSS.")
    print(f"Selected {len(items)} fresh stories; history excludes {len(previously_used)} prior stories.")
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



def fit_text(draw, text: str, max_width: int, max_lines: int, start_size: int, min_size: int = 26, bold: bool = True) -> tuple[object, list[str]]:
    """Choose a readable font size and wrap text within a fixed editorial text box.

    If the text still exceeds the line budget at min_size, trim the final line
    with an ellipsis rather than drawing outside the slide's content area.
    """
    text = clean_text(text)
    for size in range(start_size, min_size - 1, -2):
        f = font(size, bold)
        lines = wrap(draw, text, f, max_width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(min_size, bold)
    lines = wrap(draw, text, f, max_width)[:max_lines]
    if not lines:
        return f, []
    last = lines[-1]
    while last and draw.textbbox((0, 0), last + "…", font=f)[2] > max_width:
        last = last[:-1]
    lines[-1] = last.rstrip() + "…"
    return f, lines

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
    d.rectangle((0, 0, 1080, 1350), fill=PANEL)
    d.rectangle((0, 0, 14, 1350), fill=BLUE)
    d.rectangle((1066, 0, 1080, 1350), fill=BLUE)
    d.rectangle((42, 36, 1038, 1314), outline=ORANGE, width=2)
    # Restrained magazine-style corner motifs; keep the text area clean.
    d.line((850, 38, 1038, 226), fill=(232, 220, 199), width=5)
    d.line((42, 1124, 230, 1312), fill=(232, 220, 199), width=5)
    d.text((66, 58), "NEXZENCRICINFO", font=font(31, True), fill=TEAL)
    d.text((68, 108), "THE CRICKET JOURNAL  /  NEWS & INSIGHT", font=font(18, True), fill=MUTED)
    d.line((68, 160, 1012, 160), fill=ORANGE, width=2)
    d.text((68, 1263), "FOLLOW @NEXZENCRICINFO", font=font(19, True), fill=TEAL)
    d.text((855, 1261), f"{slide_no}/6  •  {date}", font=font(17, True), fill=MUTED)
    return im, d


def save_slide(im, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=95, optimize=True, subsampling=0)


def fetch_photo(article: dict[str, str], size: tuple[int, int]) -> Image.Image | None:
    """Download and crop a feed-supplied cricket image; fail closed if unusable."""
    url = article.get("image_url", "").strip()
    if not url.startswith(("https://", "http://")):
        return None
    try:
        request = Request(url, headers={"User-Agent": "NexZenCricInfo/1.0 (editorial image fetch)"})
        with urlopen(request, timeout=8) as response:
            if not response.headers.get("Content-Type", "").startswith("image/"):
                return None
            data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            return None
        with Image.open(BytesIO(data)) as source:
            photo = source.convert("RGB")
            photo.thumbnail((size[0] * 2, size[1] * 2), Image.Resampling.LANCZOS)
            target_ratio = size[0] / size[1]
            ratio = photo.width / photo.height
            if ratio > target_ratio:
                new_width = int(photo.height * target_ratio)
                left = (photo.width - new_width) // 2
                photo = photo.crop((left, 0, left + new_width, photo.height))
            else:
                new_height = int(photo.width / target_ratio)
                top = (photo.height - new_height) // 2
                photo = photo.crop((0, top, photo.width, top + new_height))
            return photo.resize(size, Image.Resampling.LANCZOS)
    except Exception as exc:
        print(f"Skipping unusable article image ({type(exc).__name__}).")
        return None


def place_photo(im: Image.Image, article: dict[str, str], bounds: tuple[int, int, int, int], overlay: int = 75) -> bool:
    """Place an image in a fixed editorial frame with a subtle dark veil."""
    left, top, right, bottom = bounds
    photo = fetch_photo(article, (right - left, bottom - top))
    if photo is None:
        return False
    veil = Image.new("RGBA", photo.size, (35, 31, 32, overlay))
    photo = Image.alpha_composite(photo.convert("RGBA"), veil).convert("RGB")
    im.paste(photo, (left, top))
    return True


def create_carousel(articles: list[dict[str, str]], date: str, directory: Path) -> list[Path]:
    paths = []
    # Cover slide with stronger hierarchy and a compact story rundown.
    im, d = base_slide(1, date)
    d.rectangle((68, 210, 1012, 1150), fill=(239, 230, 214), outline=ORANGE, width=2)
    if articles:
        place_photo(im, articles[0], (68, 210, 1012, 620), overlay=105)
    d.text((100, 260), "THE DAILY EDITION", font=font(36, True), fill=WHITE)
    d.text((95, 325), "CRICKET", font=font(100, True), fill=WHITE)
    d.text((95, 430), "JOURNAL", font=font(92, True), fill=WHITE)
    d.text((102, 555), "Five stories shaping the game today.", font=font(27), fill=WHITE)
    d.rounded_rectangle((100, 635, 980, 1055), radius=25, fill=(247, 241, 230), outline=ORANGE, width=2)
    for i, article in enumerate(articles, 1):
        y = 670 + (i - 1) * 78
        d.ellipse((130, y, 180, y + 50), fill=TEAL)
        d.text((146, y + 8), str(i), font=font(24, True), fill=WHITE)
        title_font, title_lines = fit_text(d, article["title"], 735, 2, 21, 17, True)
        for line_no, line in enumerate(title_lines):
            d.text((205, y + 2 + line_no * 25), line, font=title_font, fill=NAVY)
    d.text((105, 1090), "THE GAME, IN FIVE STORIES  /  SWIPE →", font=font(24, True), fill=BLUE)
    path = directory / "slide-1.jpg"
    save_slide(im, path)
    paths.append(path)

    for index, article in enumerate(articles, 1):
        im, d = base_slide(index + 1, date)
        d.rectangle((68, 205, 1012, 310), fill=(232, 220, 199))
        d.text((100, 238), f"THE DAILY EDITION   /   STORY {index:02d}", font=font(25, True), fill=BLUE)
        photo_ok = place_photo(im, article, (72, 330, 1008, 760), overlay=115)
        if not photo_ok:
            d.rectangle((72, 330, 1008, 760), fill=(239, 230, 214), outline=ORANGE, width=2)
            d.text((110, 520), "THE CRICKET JOURNAL", font=font(42, True), fill=BLUE)
        # Headline appears over a photo-led frame with editorial contrast.
        title_font, title_lines = fit_text(d, article["title"], 850, 4, 46, 32, True)
        title_y = 785
        title_spacing = title_font.size + 16
        for line in title_lines:
            d.text((78, title_y), line, font=title_font, fill=NAVY)
            title_y += title_spacing

        # The summary panel is anchored to the slide grid; its text has its own
        # line budget so lengthy RSS descriptions cannot spill past the footer.
        panel_top = max(820, min(title_y + 24, 850))
        panel_bottom = 1165
        d.rounded_rectangle((72, panel_top, 1008, panel_bottom), radius=26, fill=(247, 241, 230), outline=ORANGE, width=2)
        d.text((105, panel_top + 28), "THE STORY", font=font(21, True), fill=BLUE)
        summary = article.get("summary", "").strip() or "The latest development—follow the story as it unfolds."
        summary_font, summary_lines = fit_text(d, summary, 820, 5, 27, 23, False)
        sy = panel_top + 75
        line_height = summary_font.size + 13
        for line in summary_lines:
            if sy + line_height > panel_bottom - 18:
                break
            d.text((105, sy), line, font=summary_font, fill=MUTED)
            sy += line_height
        d.text((78, 1190), "NEXZENCRICINFO  •  CRICKET, CONSIDERED", font=font(19, True), fill=BLUE)
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
    slot = os.getenv("POST_SLOT", "manual").strip().lower()
    if slot not in {"morning", "evening", "night", "manual"}:
        raise RuntimeError(f"Invalid POST_SLOT: {slot!r}")
    articles = fetch_articles()
    caption = build_caption(articles, today)
    Path("drafts").mkdir(exist_ok=True)
    image_dir = Path("images") / today / slot
    image_dir.mkdir(parents=True, exist_ok=True)
    paths = create_carousel(articles, today, image_dir)
    draft = (
        f"# NexZenCricInfo — Top 5 Cricket News ({today} / {slot})\n\n{caption}\n\n"
        "## Source notes (not included in Instagram caption)\n\n"
        + "\n".join(f"{i}. {a['title']} — {a['url']}" for i, a in enumerate(articles, 1))
        + f"\n\nGenerated at {datetime.now(timezone.utc).isoformat()} (UTC)\n"
    )
    Path("drafts", f"{today}_{slot}.md").write_text(draft, encoding="utf-8")
    print(f"Created a {len(paths)}-slide carousel for {today} ({slot})")


if __name__ == "__main__":
    main()
