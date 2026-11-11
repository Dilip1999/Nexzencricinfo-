"""Render three evidence-limited, silent QA sample Reels from an approved fixture."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
NAVY = (5, 17, 48)
NAVY_LIGHT = (12, 31, 76)
CYAN = (0, 220, 245)
CYAN_DARK = (0, 120, 160)
GOLD = (255, 190, 72)
WHITE = (245, 249, 255)
MUTED = (178, 198, 224)
PURPLE = (66, 34, 130)

def font(size: int, bold: bool = False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def wrap(draw, text, face, max_width):
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=face)[2] <= max_width:
            line = trial
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def render_card(scene: dict, index: int, total: int, output: Path):
    # Match the user's supplied NexZenCricInfo reference: deep navy, electric cyan,
    # gold headline accents, framed hero area and subtle violet lower glow.
    image = Image.new("RGB", (W, H), NAVY)
    pixels = image.load()
    for y in range(H):
        t = y / max(1, H-1)
        base = tuple(int(NAVY[i] * (1-t) + NAVY_LIGHT[i] * t) for i in range(3))
        for x in range(W):
            glow = max(0.0, 1.0 - (((x-W*0.52)/(W*0.8))**2 + ((y-H*0.94)/(H*0.42))**2))
            pixels[x, y] = tuple(min(255, int(base[i] + PURPLE[i]*glow*0.24)) for i in range(3))
    draw = ImageDraw.Draw(image)
    # Outer neon frame and inner content frame
    draw.rounded_rectangle((20, 20, W-20, H-20), radius=36, outline=CYAN, width=4)
    draw.rounded_rectangle((42, 42, W-42, H-42), radius=28, outline=CYAN_DARK, width=2)
    draw.text((72, 76), "NEXZENCRICINFO", font=font(39, True), fill=WHITE)
    draw.text((72, 132), "NEXT GEN CRICKET  /  NEWS  •  RECORDS  •  INSIGHT", font=font(21, True), fill=MUTED)
    draw.line((72, 190, W-72, 190), fill=CYAN, width=3)

    # Hero visual panel: designed as a deliberate photo slot. Actual player imagery
    # is not fabricated; approved/licensed portraits can be inserted in a later pass.
    hero_top, hero_bottom = 235, 1030
    draw.rounded_rectangle((62, hero_top, W-62, hero_bottom), radius=26, fill=(8, 24, 59), outline=CYAN, width=3)
    draw.rounded_rectangle((78, hero_top+16, W-78, hero_bottom-16), radius=18, outline=CYAN_DARK, width=2)
    mid = W//2
    draw.line((mid, hero_top+32, mid, hero_bottom-32), fill=CYAN, width=3)
    # Stylized cricket graphic panels, clearly illustrative rather than fake portraits.
    for left, right, label, sub in [
        (94, mid-12, "BAT", "PLAYER PERFORMANCE"),
        (mid+12, W-94, "BALL", "MATCH IMPACT"),
    ]:
        cx = (left+right)//2
        draw.ellipse((cx-112, hero_top+150, cx+112, hero_top+374), outline=CYAN_DARK, width=5)
        draw.line((cx-70, hero_top+344, cx+72, hero_top+206), fill=GOLD, width=17)
        draw.line((cx-78, hero_top+357, cx+60, hero_top+219), fill=WHITE, width=5)
        draw.text((left+16, hero_top+490), label, font=font(36, True), fill=CYAN)
        draw.text((left+16, hero_top+548), sub, font=font(18, True), fill=MUTED)

    eyebrow = scene["eyebrow"].upper()
    draw.text((88, 1090), eyebrow, font=font(27, True), fill=CYAN)
    title_font = font(76, True)
    title_lines = wrap(draw, scene["title"], title_font, W-176)
    y = 1160
    for line in title_lines[:2]:
        draw.text((88, y), line, font=title_font, fill=WHITE)
        y += 92
    body_y = y + 18
    for line in wrap(draw, scene["body"], font(40, True), W-176)[:3]:
        draw.text((90, body_y), line, font=font(40, True), fill=GOLD)
        body_y += 58
    note_y = body_y + 28
    for line in wrap(draw, scene.get("note", ""), font(23), W-176)[:3]:
        draw.text((90, note_y), line, font=font(23), fill=MUTED)
        note_y += 36

    draw.line((88, H-245, W-88, H-245), fill=GOLD, width=2)
    draw.text((88, H-205), "NEXZENCRICINFO  •  CRICKET STORIES WITH CONTEXT", font=font(21, True), fill=CYAN)
    draw.text((88, H-155), "QA SAMPLE ONLY  •  NOT APPROVED FOR PUBLICATION", font=font(19, True), fill=MUTED)
    draw.text((W-145, H-155), f"{index:02d}/{total:02d}", font=font(22, True), fill=WHITE)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=94)

def render_reel(title: str, scenes: list[dict], output_dir: Path, slug: str):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render sample Reels.")
    frame_dir = output_dir / slug / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for i, scene in enumerate(scenes, 1):
        render_card(scene, i, len(scenes), frame_dir / f"slide-{i:02d}.jpg")
    concat = frame_dir / "concat.txt"
    lines = []
    for i in range(1, len(scenes)+1):
        lines.append("file '" + str((frame_dir / f"slide-{i:02d}.jpg").resolve()) + "'")
        lines.append("duration 3")
    lines.append("file '" + str((frame_dir / f"slide-{len(scenes):02d}.jpg").resolve()) + "'")
    concat.write_text("\n".join(lines)+"\n", encoding="utf-8")
    output = output_dir / slug / f"{slug}.mp4"
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
        "-safe", "0", "-i", str(concat), "-vf", "fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-movflags", "+faststart", str(output)
    ], check=True, capture_output=True, text=True)
    return output

def build_sample_batch(output_dir: Path):
    source_url = "https://cricketdatabase.com/matches/2026-11-09-royal-desert-champions-v-united-tigers"
    source = "Cricket Database scorecard (match-level figures)"
    pending = "Scorecard review pending: innings extras do not reconcile in normalized data and listing format conflicts with competition label. Not approved for publication."
    common = [
        {"eyebrow":"Stats & Analytics","title":"45 off 21: the acceleration","body":"Fakhar Zaman  •  45 runs  •  21 balls  •  SR 214.29","note":"A single-match performance, not a career or season record."},
        {"eyebrow":"Stats & Analytics","title":"The impact with the ball","body":"Abbas Afridi  •  3 wickets  •  10 runs  •  2 overs","note":"Match figures as listed on the source scorecard."},
        {"eyebrow":"Stats & Analytics","title":"Read the numbers in context","body":"One scorecard. Two standout contributions. No career-level conclusions.","note":pending},
    ]
    battles = [
        {"eyebrow":"Player comparison","title":"Two batting contributions","body":"Fakhar Zaman 45 off 21  •  SR 214.29","note":"Compared with Waseem Muhammad's innings in the same scorecard."},
        {"eyebrow":"Player comparison","title":"Waseem Muhammad","body":"24 off 17  •  SR 141.18","note":"Strike rates calculated from the listed runs and balls."},
        {"eyebrow":"Player comparison","title":"Different scoring tempo","body":"Fakhar: +73.11 strike-rate points in this innings","note":"This is a same-match performance comparison, not a direct batter-v-bowler matchup or career comparison."},
    ]
    analyst = [
        {"eyebrow":"Match Intelligence","title":"A short successful chase","body":"United Tigers 84/1  •  7 overs","note":"Chase figures from the scorecard listing."},
        {"eyebrow":"Match Intelligence","title":"The result","body":"United Tigers won by 9 wickets","note":"As stated in the provider scorecard."},
        {"eyebrow":"Match Intelligence","title":"What we can say","body":"The chase reached 84 with one wicket down in seven overs.","note":"No unsupported tactical cause is inferred from the available summary. "+pending},
    ]
    items = [
        {"slug":"stats-analytics","title":"Stats & Analytics: Fakhar and Abbas", "pillar":"stats", "scenes":common},
        {"slug":"player-comparison","title":"Player Comparison: Fakhar and Waseem", "pillar":"battles", "scenes":battles},
        {"slug":"match-intelligence","title":"Match Intelligence: United Tigers chase", "pillar":"analyst", "scenes":analyst},
    ]
    manifest = {"status":"qa_sample_only","publish_eligible":False,"audio":"silent review render; add licensed/original soundtrack only after owner approval","source":{"name":source,"url":source_url},"data_quality_note":pending,"reels":[]}
    for item in items:
        path = render_reel(item["title"], item["scenes"], output_dir, item["slug"])
        manifest["reels"].append({"title":item["title"],"slug":item["slug"],"pillar":item["pillar"],"video":str(path),"duration_seconds":len(item["scenes"])*3,"scene_count":len(item["scenes"])})
        storyboard = ["# "+item["title"], "", "**QA SAMPLE ONLY — NOT FOR PUBLICATION**", "", pending, "", "Source: "+source+" — "+source_url, ""]
        for i, scene in enumerate(item["scenes"],1):
            storyboard += [f"## Scene {i}", f"**{scene['eyebrow']}**", f"**{scene['title']}**", scene["body"], scene.get("note",""), ""]
        (output_dir/item["slug"]/"storyboard.md").write_text("\n".join(storyboard),encoding="utf-8")
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"sample-batch-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__ == "__main__":
    result=build_sample_batch(Path("qa-sample-reels"))
    print(f"Rendered {len(result['reels'])} silent QA Reels. Publication eligible: {result['publish_eligible']}.")
