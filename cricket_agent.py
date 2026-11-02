"""Generate an engaging six-slide Top 5 cricket news carousel."""
from __future__ import annotations

import html
import json
import os
import re
from html.parser import HTMLParser
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
from opencricket_client import fetch_matches, match_to_article

try:
    from googlenewsdecoder import gnewsdecoder
except ImportError:  # Keep draft generation resilient if the optional resolver is unavailable.
    gnewsdecoder = None
from PIL import Image, ImageDraw, ImageFont

IST = ZoneInfo("Asia/Kolkata")
NEWS_FEED = "https://news.google.com/rss/search?q=cricket+(India+OR+IPL+OR+ICC+OR+Test+OR+ODI+OR+T20)&hl=en-IN&gl=IN&ceid=IN:en"
MAX_ARTICLES = 5
MAX_RSS_LINKS_TO_RESOLVE = 30
SIZE = (1080, 1350)
NAVY = (12, 20, 54)       # Premium deep navy
PANEL = (22, 39, 92)       # Royal-blue panel
BLUE = (35, 116, 245)      # Brand blue
TEAL = (0, 214, 232)       # Cyan accent
ORANGE = (245, 190, 75)    # Restrained gold highlight
GOLD = (245, 190, 75)
WHITE = (255, 255, 255)
MUTED = (203, 218, 246)    # High-contrast pale blue


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


# Hard editorial exclusion: Pakistan and Bangladesh stories must not be published.
EXCLUDED_COUNTRY_RE = re.compile(
    r"\b(?:pakistan(?:i|is)?|bangladesh(?:i|is)?)\b", re.IGNORECASE
)


def is_excluded_story(article: dict[str, str]) -> bool:
    """Reject restricted-country stories across headline, summary, and metadata."""
    searchable_text = " ".join(
        str(article.get(field, ""))
        for field in ("title", "summary", "description", "content", "source")
    )
    return bool(EXCLUDED_COUNTRY_RE.search(clean_text(searchable_text)))




def extract_image_urls(entry) -> list[str]:
    """Collect image URLs from common RSS media/enclosure/content fields."""
    urls = []
    for field in ("media_thumbnail", "media_content", "enclosures"):
        values = entry.get(field, []) or []
        if isinstance(values, dict):
            values = [values]
        for item in values:
            if isinstance(item, dict):
                url = str(item.get("url") or item.get("href") or "").strip()
                mime = str(item.get("type") or "").lower()
                if url and (not mime or mime.startswith("image/")):
                    urls.append(url)
    for field in ("image", "thumbnail"):
        item = entry.get(field)
        if isinstance(item, dict):
            url = str(item.get("href") or item.get("url") or "").strip()
            if url:
                urls.append(url)
    # Google News frequently includes image links in the HTML description.
    html_blob = " ".join(str(entry.get(field, "")) for field in ("summary", "content"))
    for match in re.findall(r'<img[^>]+(?:src|data-src)=[\"\']([^\"\']+)', html_blob, re.IGNORECASE):
        if match.startswith(("https://", "http://")):
            urls.append(html.unescape(match))
    # Deduplicate while preserving source order.
    return list(dict.fromkeys(urls))


def image_url_is_usable(url: str) -> bool:
    """Validate a candidate image and log why it was rejected."""
    if not url.startswith(("https://", "http://")):
        print("Image candidate rejected: URL is not HTTP(S).")
        return False
    # Keep logs concise: don't print potentially long signed query strings.
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    label = f"{parsed.netloc}{parsed.path[:90]}"
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NexZenCricInfo/1.0)"})
        with urlopen(request, timeout=8) as response:
            content_type = response.headers.get("Content-Type", "").lower().split(";")[0].strip()
            if not content_type.startswith("image/"):
                print(f"Image candidate rejected ({label}): content-type={content_type or 'missing'}.")
                return False
            data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            print(f"Image candidate rejected ({label}): exceeds 8 MiB limit.")
            return False
        with Image.open(BytesIO(data)) as im:
            width, height = im.size
            if im.format not in {"JPEG", "PNG", "WEBP"}:
                print(f"Image candidate rejected ({label}): unsupported format={im.format}.")
                return False
            if width < 480 or height < 260:
                print(f"Image candidate rejected ({label}): dimensions={width}x{height}, minimum is 480x260.")
                return False
            print(f"Image candidate accepted ({label}): {im.format} {width}x{height}.")
            return True
    except Exception as exc:
        print(f"Image candidate rejected ({label}): {type(exc).__name__}: {str(exc)[:180]}")
        return False


def image_url_variants(url: str) -> list[str]:
    """Try larger versions of Google-hosted image thumbnails."""
    if not url:
        return []

    variants = [url]

    if "googleusercontent.com" in url:
        # Google News thumbnails often end with a size parameter, e.g. =s0-w300.
        base = url.split("=", 1)[0]
        variants.extend([
            f"{base}=s0",
            f"{base}=w1200",
            f"{base}=s0-w1200",
        ])

    return list(dict.fromkeys(variants))


def first_usable_image(urls: list[str]) -> str:
    """Return the first image candidate that passes validation."""
    for url in urls:
        for candidate in image_url_variants(url):
            if image_url_is_usable(candidate):
                return candidate

    return ""

class _ArticleImageParser(HTMLParser):
    """Collect social-preview and embedded image URLs from publisher HTML."""

    def __init__(self):
        super().__init__()
        self.image_urls = []

    def handle_starttag(self, tag, attrs):
        values = {str(key).lower(): str(value or "").strip()
                  for key, value in attrs if key}
        if tag.lower() == "meta":
            prop = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "")
            if content and prop in {"og:image", "og:image:url", "twitter:image",
                                    "twitter:image:src"}:
                self.image_urls.append(content)
        elif tag.lower() in {"img", "source"}:
            for field in ("src", "data-src", "data-original", "data-lazy-src"):
                if values.get(field):
                    self.image_urls.append(values[field])
            # Responsive image sets often contain the largest usable image.
            srcset = values.get("srcset") or values.get("data-srcset", "")
            for entry in srcset.split(","):
                candidate = entry.strip().split()
                if candidate:
                    self.image_urls.append(candidate[0])


def extract_page_image_url(article_url: str) -> str:
    """Find a real usable image in publisher social metadata or page markup."""
    if not article_url.startswith(("https://", "http://")):
        return ""
    try:
        request = Request(
            article_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NexZenCricInfo/1.0; +https://github.com/Dilip1999/Nexzencricinfo-)"},
        )
        with urlopen(request, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                return ""
            page = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            page_url = response.geturl()
        parser = _ArticleImageParser()
        parser.feed(page)
        candidates = []
        for raw in parser.image_urls:
            candidate = html.unescape(raw).strip()
            if candidate.startswith("//"):
                candidate = "https:" + candidate
            candidate = urljoin(page_url, candidate)
            if candidate.startswith(("https://", "http://")):
                candidates.append(candidate)
        # Check candidates one at a time, with de-duplication and existing
        # dimension/format/size validation. Do not substitute placeholders.
        for candidate in dict.fromkeys(candidates):
            if image_url_is_usable(candidate):
                return candidate
    except Exception as exc:
        print(f"Could not inspect publisher image markup ({type(exc).__name__}).")
    return ""


def resolve_google_news_urls(urls: list[str]) -> dict[str, str]:
    """Resolve Google News wrapper URLs to their publisher article URLs in one batch."""
    if not urls:
        return {}
    if gnewsdecoder is None:
        print("Google News URL decoder is unavailable; publisher-page image lookup is skipped.")
        return {}

    try:
        results = gnewsdecoder(urls, interval=0.15, timeout=12.0)
        if isinstance(results, dict):
            results = [results]
        resolved = {}
        for original, result in zip(urls, results):
            if isinstance(result, dict) and result.get("success") and result.get("decoded_url"):
                destination = str(result["decoded_url"]).strip()
                if destination.startswith(("https://", "http://")):
                    resolved[original] = destination
        print(f"Resolved {len(resolved)} of {len(urls)} Google News publisher URLs.")
        return resolved
    except Exception as exc:
        print(f"Google News URL resolution failed ({type(exc).__name__}: {str(exc)[:160]}).")
        return {}


def fetch_articles() -> list[dict[str, str]]:
    """Combine fresh eligible OpenCricket match data with Google News RSS."""
    history_path = Path("content_history.json")
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"stories": []}
    previously_used = {story_key(str(item.get("title", ""))) for item in history.get("stories", [])}
    items, seen = [], set()
    excluded_count = 0

    try:
        for match in fetch_matches():
            article = match_to_article(match)
            if not article:
                continue
            if is_excluded_story(article):
                excluded_count += 1
                print(f"Excluded restricted-country OpenCricket story: {article.get('title', '')}")
                continue
            key = story_key(article["title"])
            if not key or key in previously_used or key in seen:
                continue

            # Resolve photos only for stories that pass the editorial filter.
            api_candidates = [str(article.get("image_url") or "").strip()]
            api_candidates.extend(article.get("image_candidates", []))
            valid_image = first_usable_image(
                [candidate for candidate in api_candidates if candidate]
            )
            if not valid_image:
                valid_image = extract_page_image_url(str(article.get("url") or ""))
            if not valid_image:
                print(f"Skipping OpenCricket story without a usable photo: {article.get('title', '')}")
                continue
            article["image_url"] = valid_image
            seen.add(key)
            items.append(article)
            if len(items) >= MAX_ARTICLES:
                break
    except Exception as exc:
        print(f"OpenCricket API unavailable; using RSS fallback ({type(exc).__name__}).")

    feed = feedparser.parse(NEWS_FEED)
    rss_candidates = []
    for entry in feed.entries:
        title = clean_text(str(entry.get("title", "")))
        url = str(entry.get("link", "")).strip()
        key = story_key(title)
        if not title or not url or key in seen or key in previously_used:
            continue

        article = {
            "title": title,
            "url": url,
            "summary": clean_summary(str(entry.get("summary", "")), title),
            "source": "Google News RSS",
            "image_candidates": extract_image_urls(entry),
        }
        if is_excluded_story(article):
            excluded_count += 1
            print(f"Excluded restricted-country RSS story: {title}")
            continue
        rss_candidates.append(article)
        if len(rss_candidates) >= MAX_RSS_LINKS_TO_RESOLVE:
            break

    # Google News RSS links are wrappers. Resolve them before requesting the
    # publisher's Open Graph/Twitter image metadata.
    wrapped_urls = [
        article["url"] for article in rss_candidates
        if article["url"].startswith("https://news.google.com/")
        or article["url"].startswith("http://news.google.com/")
    ]
    resolved_urls = resolve_google_news_urls(wrapped_urls)

    for article in rss_candidates:
        title = article["title"]
        original_url = article["url"]
        publisher_url = resolved_urls.get(original_url, original_url)
        article["url"] = publisher_url

        publisher_candidates = [
            candidate for candidate in article["image_candidates"]
            if "googleusercontent.com" not in candidate
            and "news.google.com" not in candidate
        ]
        valid_image = first_usable_image(publisher_candidates)
        if not valid_image and "news.google.com" not in publisher_url:
            valid_image = extract_page_image_url(publisher_url)
        if not valid_image:
            print(f"Skipping story without a usable publisher photo: {title}")
            continue

        article["image_url"] = valid_image
        key = story_key(title)
        seen.add(key)
        items.append(article)
        if len(items) >= MAX_ARTICLES:
            break

    if not items:
        raise RuntimeError("No fresh eligible cricket stories found from OpenCricket API or RSS.")
    print(
        f"Selected {len(items)} eligible fresh stories; excluded {excluded_count} "
        f"Pakistan/Bangladesh stories; history excludes {len(previously_used)} prior stories."
    )
    return items

def fit_text_in_box(draw, text: str, max_width: int, max_height: int,
                    start_size: int = 48, min_size: int = 22,
                    line_spacing: int = 6, bold: bool = True):
    """Fit every word of a headline inside a measured area without ellipsis."""
    text = clean_text(text)
    for size in range(start_size, min_size - 1, -2):
        typeface = font(size, bold)
        lines = wrap(draw, text, typeface, max_width)
        total_height = len(lines) * (typeface.size + line_spacing) - line_spacing
        if total_height <= max_height:
            return typeface, lines
    # Retain the complete headline at the smallest supported size as a final
    # fallback. The 230px title region accommodates normal cricket headlines.
    typeface = font(min_size, bold)
    return typeface, wrap(draw, text, typeface, max_width)


def gradient_background():
    """Create the brand's navy-to-royal-blue-to-violet sports gradient."""
    im = Image.new("RGB", SIZE, NAVY)
    pix = im.load()
    stops = [(0.0, (8, 18, 55)), (0.52, (25, 76, 190)), (1.0, (104, 42, 190))]
    for y in range(SIZE[1]):
        t = y / max(1, SIZE[1] - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                q = (t - t0) / (t1 - t0)
                color = tuple(int(c0[k] * (1-q) + c1[k] * q) for k in range(3))
                break
        for x in range(SIZE[0]):
            pix[x, y] = color
    return im


def base_slide(slide_no: int, date: str):
    im = gradient_background()
    d = ImageDraw.Draw(im)
    # Consistent high-contrast cricket media frame and compact editorial header.
    d.rectangle((24, 24, 1056, 1326), outline=TEAL, width=3)
    d.text((62, 42), "NEXZENCRICINFO", font=font(32, True), fill=WHITE)
    d.text((62, 91), "NEXT GEN CRICKET  /  NEWS • RECORDS • INSIGHT", font=font(18, True), fill=MUTED)
    d.line((62, 140, 1018, 140), fill=TEAL, width=3)
    d.text((62, 1270), "@NEXZENCRICINFO", font=font(20, True), fill=WHITE)
    d.text((850, 1270), f"{slide_no}/6  •  {date}", font=font(18, True), fill=MUTED)
    return im, d


def save_slide(im, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=95, optimize=True, subsampling=0)


def fetch_photo(article: dict[str, str], size: tuple[int, int]) -> Image.Image | None:
    """Try feed image candidates and return the first usable cropped photo."""
    urls = [article.get("image_url", "").strip()]
    urls.extend(article.get("image_candidates", []))

    expanded_urls = []
    for url in dict.fromkeys(urls):
        expanded_urls.extend(image_url_variants(url))

    for url in dict.fromkeys(expanded_urls):
        if not url.startswith(("https://", "http://")):
            continue
        try:
            request = Request(url, headers={"User-Agent": "NexZenCricInfo/1.0 (editorial image fetch)"})
            with urlopen(request, timeout=8) as response:
                if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                    continue
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                continue
            with Image.open(BytesIO(data)) as source:
                photo = source.convert("RGB")
                if photo.width < 480 or photo.height < 260:
                    continue
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

def place_photo(im: Image.Image, article: dict[str, str], bounds: tuple[int, int, int, int], overlay: int = 0) -> bool:
    """Place a bright, clear cricket photograph in a fixed editorial frame."""
    left, top, right, bottom = bounds
    photo = fetch_photo(article, (right - left, bottom - top))
    if photo is None:
        return False
    if overlay > 0:
        veil = Image.new("RGBA", photo.size, (5, 13, 30, overlay))
        photo = Image.alpha_composite(photo.convert("RGBA"), veil).convert("RGB")
    im.paste(photo, (left, top))
    return True


def apply_bottom_gradient(im: Image.Image, bounds: tuple[int, int, int, int],
                          start_alpha: int = 0, end_alpha: int = 225) -> None:
    """Add a smooth dark fade at a photo's lower edge so headlines remain legible."""
    left, top, right, bottom = bounds
    height = max(1, bottom - top)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for offset in range(height):
        progress = offset / max(1, height - 1)
        alpha = int(start_alpha + (end_alpha - start_alpha) * progress)
        draw.line((left, top + offset, right, top + offset),
                  fill=(4, 15, 34, alpha), width=1)
    im.alpha_composite(layer) if im.mode == "RGBA" else im.paste(
        Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    )


def draw_centered_lines(draw, lines: list[str], typeface, center_x: int,
                        top: int, fill, spacing: int = 8) -> int:
    """Draw each line centered and return the y position after the final line."""
    y = top
    for line in lines:
        bounds = draw.textbbox((0, 0), line, font=typeface)
        width = bounds[2] - bounds[0]
        draw.text((center_x - width // 2, y), line, font=typeface, fill=fill)
        y += typeface.size + spacing
    return y


def create_carousel(articles: list[dict[str, str]], date: str, directory: Path) -> list[Path]:
    paths = []

    # COVER: keep the cricketers as the hero. The title sits across the
    # middle/lower part of the photograph, with no numbered headline list.
    im, d = base_slide(1, date)
    cover_bounds = (62, 175, 1018, 900)
    d.rounded_rectangle((50, 160, 1030, 1165), radius=30,
                        fill=NAVY, outline=TEAL, width=3)
    if articles:
        if not place_photo(im, articles[0], cover_bounds, overlay=0):
            raise RuntimeError("Could not place the cover cricket photograph.")
    apply_bottom_gradient(im, (62, 590, 1018, 900), start_alpha=0, end_alpha=225)
    d = ImageDraw.Draw(im)
    d.rectangle((61, 174, 1019, 901), outline=TEAL, width=2)

    d.text((540, 650), "THE DAILY CRICKET", font=font(30, True),
           fill=TEAL, anchor="mm")
    top_font = font(112, True)
    second_font = font(68, True)
    draw_centered_lines(d, ["TOP 5"], top_font, 540, 700, WHITE, spacing=0)
    draw_centered_lines(d, ["CRICKET STORIES"], second_font, 540, 805, GOLD, spacing=0)

    d.line((150, 975, 930, 975), fill=GOLD, width=3)
    d.text((540, 1028), "THE BIGGEST CRICKET UPDATES OF THE DAY",
           font=font(24, True), fill=MUTED, anchor="mm")
    d.text((540, 1092), "SWIPE TO READ THE FIVE STORIES  →",
           font=font(22, True), fill=TEAL, anchor="mm")

    path = directory / "slide-1.jpg"
    save_slide(im, path)
    paths.append(path)

    # STORY SLIDES: large unobstructed photograph, then a dedicated headline
    # area. The old "THE STORY" summary card is removed completely so it can
    # never cover or clip a long headline.
    for index, article in enumerate(articles, 1):
        im, d = base_slide(index + 1, date)
        d.rounded_rectangle((55, 160, 1025, 1165), radius=28,
                            fill=(13, 28, 75), outline=TEAL, width=3)

        d.text((82, 195), "DAILY CRICKET", font=font(25, True), fill=TEAL)
        d.text((330, 195), f"/  STORY {index:02d}  /  05",
               font=font(25, True), fill=GOLD)
        # Five small progress markers reinforce the carousel sequence.
        marker_x = 820
        for marker in range(5):
            radius = 8
            cx = marker_x + marker * 34
            color = GOLD if marker == index - 1 else MUTED
            d.ellipse((cx - radius, 188 - radius, cx + radius, 188 + radius),
                      outline=color, fill=color if marker == index - 1 else None,
                      width=2)

        photo_bounds = (78, 245, 1002, 820)
        photo_ok = place_photo(im, article, photo_bounds, overlay=0)
        if not photo_ok:
            raise RuntimeError(f"Missing usable cricket photo for story: {article.get('title', '')}")
        apply_bottom_gradient(im, (78, 625, 1002, 820),
                              start_alpha=0, end_alpha=215)
        d = ImageDraw.Draw(im)
        d.rectangle((77, 244, 1003, 821), outline=TEAL, width=2)

        # Title occupies its own measured region with adaptive sizing;
        # no overlaying summary panel or shortened headline.
        title_font, title_lines = fit_text_in_box(
            d, article["title"], max_width=850, max_height=230,
            start_size=48, min_size=22, line_spacing=6, bold=True
        )
        title_y = 842
        line_spacing = 6
        for line in title_lines:
            d.text((92, title_y), line, font=title_font, fill=WHITE,
                   stroke_width=1, stroke_fill=(4, 15, 34))
            title_y += title_font.size + line_spacing

        # A simple gold cricket-ball divider replaces the former highlighted
        # summary box. Story descriptions remain in the post caption/draft.
        divider_y = 1110
        d.line((125, divider_y, 465, divider_y), fill=GOLD, width=3)
        d.line((615, divider_y, 955, divider_y), fill=GOLD, width=3)
        d.ellipse((520, divider_y - 25, 560, divider_y + 15),
                  outline=GOLD, width=3)
        d.line((530, divider_y + 7, 550, divider_y - 17), fill=GOLD, width=2)

        d.text((78, 1190), "NEXZENCRICINFO  •  NEXT GEN CRICKET",
               font=font(18, True), fill=TEAL)
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
    try:
        articles = fetch_articles()
    except RuntimeError as exc:
        if "No fresh cricket stories found" in str(exc):
            print("No eligible fresh cricket stories today; skipping carousel generation.")
            return
        raise
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
