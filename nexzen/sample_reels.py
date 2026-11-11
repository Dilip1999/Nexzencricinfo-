"""Render three evidence-limited, silent QA sample Reels from an approved fixture."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
IVORY = (246, 241, 229)
BURGUNDY = (105, 24, 48)
CHARCOAL = (34, 33, 32)
GOLD = (181, 145, 77)
MUTED = (108, 99, 88)

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
    image = Image.new("RGB", (W, H), IVORY)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, W, 26), fill=BURGUNDY)
    draw.text((76, 82), "NEXZENCRICINFO", font=font(34, True), fill=CHARCOAL)
    draw.text((76, 132), "THE CRICKET JOURNAL  /  EDITORIAL EDITION", font=font(19), fill=MUTED)
    draw.line((76, 190, W-76, 190), fill=GOLD, width=3)
    draw.text((76, 270), scene["eyebrow"].upper(), font=font(25, True), fill=BURGUNDY)
    title_font = font(78, True)
    y = 370
    for line in wrap(draw, scene["title"], title_font, W-152):
        draw.text((76, y), line, font=title_font, fill=CHARCOAL)
        y += 100
    y += 52
    draw.rounded_rectangle((76, y, W-76, y+430), radius=28, fill=CHARCOAL)
    body_font = font(47, True)
    body_y = y+76
    for line in wrap(draw, scene["body"], body_font, W-230):
        draw.text((116, body_y), line, font=body_font, fill=IVORY)
        body_y += 66
    if scene.get("note"):
        note_y = y+460
        for line in wrap(draw, scene["note"], font(27), W-152):
            draw.text((76, note_y), line, font=font(27), fill=MUTED)
            note_y += 42
    draw.line((76, H-220, W-76, H-220), fill=GOLD, width=2)
    draw.text((76, H-175), "SCORECARD REVIEW PENDING  •  QA SAMPLE ONLY", font=font(23, True), fill=BURGUNDY)
    draw.text((W-150, H-175), f"{index:02d}/{total:02d}", font=font(23, True), fill=CHARCOAL)
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
        lines.append(f"file 'slide-{i:02d}.jpg'")
        lines.append("duration 3")
    lines.append(f"file 'slide-{len(scenes):02d}.jpg'")
    concat.write_text("\\n".join(lines)+"\\n", encoding="utf-8")
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
        manifest["reels"].append({"title":item["title"],"pillar":item["pillar"],"video":str(path),"duration_seconds":len(item["scenes"])*3,"scene_count":len(item["scenes"])})
        storyboard = ["# "+item["title"], "", "**QA SAMPLE ONLY — NOT FOR PUBLICATION**", "", pending, "", "Source: "+source+" — "+source_url, ""]
        for i, scene in enumerate(item["scenes"],1):
            storyboard += [f"## Scene {i}", f"**{scene['eyebrow']}**", f"**{scene['title']}**", scene["body"], scene.get("note",""), ""]
        (output_dir/item["slug"]/"storyboard.md").write_text("\\n".join(storyboard),encoding="utf-8")
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"sample-batch-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__ == "__main__":
    result=build_sample_batch(Path("qa-sample-reels"))
    print(f"Rendered {len(result['reels'])} silent QA Reels. Publication eligible: {result['publish_eligible']}.")
