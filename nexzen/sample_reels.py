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
    background_path = Path(scene.get("background_image", ""))
    if background_path.is_file():
        source = Image.open(background_path).convert("RGB")
        # Cover the full vertical canvas while keeping the player near the center.
        scale = max(W / source.width, H / source.height)
        resized = source.resize((int(source.width * scale), int(source.height * scale)), Image.Resampling.LANCZOS)
        left = max(0, (resized.width - W) // 2)
        top = max(0, (resized.height - H) // 2)
        image = resized.crop((left, top, left + W, top + H))
        # Dark navy treatment keeps the real player visible behind legible editorial text.
        navy_overlay = Image.new("RGB", (W, H), NAVY)
        image = Image.blend(image, navy_overlay, 0.56)
        # Strengthen the lower text zone without hiding the player's silhouette.
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shade_draw = ImageDraw.Draw(shade)
        shade_draw.rectangle((0, 210, W, H), fill=(3, 13, 37, 65))
        image = Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB")
    else:
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

    # Story-first layout: no oversized decorative placeholder panel.
    eyebrow = scene["eyebrow"].upper()
    draw.text((88, 270), eyebrow, font=font(27, True), fill=CYAN)
    title_font = font(76, True)
    title_lines = wrap(draw, scene["title"], title_font, W-176)
    y = 350
    for line in title_lines[:2]:
        draw.text((88, y), line, font=title_font, fill=WHITE)
        y += 92
    body_y = y + 18
    for line in wrap(draw, scene["body"], font(40, True), W-176)[:3]:
        draw.text((90, body_y), line, font=font(40, True), fill=GOLD)
        body_y += 58
    note_y = body_y + 42
    for line in wrap(draw, scene.get("note", ""), font(23), W-176)[:3]:
        draw.text((90, note_y), line, font=font(23), fill=MUTED)
        note_y += 36


    if scene.get("spotlight_value") and scene.get("spotlight_label"):
        panel_top = min(max(note_y + 70, 850), 1260)
        panel_bottom = panel_top + 250
        draw.rounded_rectangle((76, panel_top, W-76, panel_bottom), radius=24,
                               fill=(8, 29, 68), outline=CYAN_DARK, width=2)
        draw.text((112, panel_top+28), scene["spotlight_label"].upper(),
                  font=font(22, True), fill=CYAN)
        draw.text((112, panel_top+78), scene["spotlight_value"],
                  font=font(72, True), fill=GOLD)

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
        lines.append("duration 4")
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
    """Build one selective story from the user's supplied India-NZ scorecard screenshot."""
    fixture_path = Path(__file__).parent / "fixtures" / "india_nz_1st_odi_2026_sample.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    source = fixture["provenance"]
    limitations = " ".join(fixture["limitations"])
    scenes = [
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"THE HOOK","title":"Seven short of a hundred.","body":"Virat Kohli  •  93 off 91 balls","note":"8 fours  •  1 six  •  Strike rate 102.20","spotlight_value":"93","spotlight_label":"Runs from 91 balls","voiceover":"Seven runs short of a hundred. Virat Kohli made 93 from 91 balls against New Zealand in the first ODI."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"THE SUPPORTING STORY","title":"The innings around him","body":"Gill 56  •  Iyer 49","note":"Two more major contributions on India's scorecard.","voiceover":"Kohli wasn't the only contributor. Shubman Gill scored 56, while Shreyas Iyer added 49."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"THE SCOREBOARD","title":"India reached 306 for 6","body":"49 overs  •  India won by 4 wickets","note":"Score and result exactly as shown in the supplied screenshot.","spotlight_value":"306/6","spotlight_label":"India innings total","voiceover":"India's innings finished at 306 for six in 49 overs, and the scorecard records a four-wicket win."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"THE DETAIL","title":"A century that stayed just out of reach","body":"93 runs  •  8 boundaries for four  •  1 six","note":"Kohli was dismissed, caught by Michael Bracewell off Kyle Jamieson, according to the visible scorecard.","voiceover":"Kohli's 93 included eight fours and one six. The scorecard shows him caught by Michael Bracewell off Kyle Jamieson."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"JOIN THE DEBATE","title":"Was 93 the defining innings?","body":"Kohli 93  •  Gill 56  •  Iyer 49","note":"Based only on the visible India innings. First-innings context is not shown.","voiceover":"Which innings stood out most to you — Kohli's 93, Gill's 56, or Iyer's 49? Tell us in the comments."}
    ]
    item = {"slug":"india-nz-kohli-93-story","title":"India vs New Zealand: Kohli's 93", "pillar":"stats", "scenes":scenes}
    manifest = {
        "status":"qa_sample_only",
        "publish_eligible":False,
        "audio":"silent review render; voiceover script included; soundtrack and narration not yet added",
        "source":{"name":source,"match":fixture["match"],"venue":fixture["venue"]},"player_image":{"player":"Virat Kohli","source":"Wikimedia Commons","author":"lensbug.chandru","license":"CC BY 2.0","license_url":"https://creativecommons.org/licenses/by/2.0/","source_url":"https://commons.wikimedia.org/wiki/File:Virat_Kohli_Batting.jpg","usage_note":"Archival illustrative photo; not represented as a photo from the 2026 match."},
        "data_quality_note":limitations,
        "selection_policy":"One high-potential story from this supplied scorecard; not every match becomes content.",
        "reels":[]
    }
    path = render_reel(item["title"], item["scenes"], output_dir, item["slug"])
    manifest["reels"].append({"title":item["title"],"slug":item["slug"],"pillar":item["pillar"],"video":str(path),"duration_seconds":len(item["scenes"])*4,"scene_count":len(item["scenes"])})
    storyboard = [
        "# "+item["title"], "",
        "**QA SAMPLE ONLY — NOT FOR PUBLICATION**", "",
        "**Source:** "+source, "",
        "**Match:** "+fixture["match"], "",
        "**Venue:** "+fixture["venue"], "",
        "**Result:** "+fixture["result"], "",
        "**Limitations:** "+limitations, "", "**Player background image:** Virat Kohli, photo by lensbug.chandru, Wikimedia Commons, CC BY 2.0. Archival image, not from the 2026 match. https://commons.wikimedia.org/wiki/File:Virat_Kohli_Batting.jpg", ""
    ]
    for i, scene in enumerate(item["scenes"],1):
        storyboard += [f"## Scene {i}", f"**{scene['eyebrow']}**", f"**{scene['title']}**", scene["body"], scene.get("note",""), "", "**Voiceover:** "+scene.get("voiceover",""), ""]
    (output_dir/item["slug"]/"storyboard.md").write_text("\n".join(storyboard),encoding="utf-8")
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"sample-batch-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__ == "__main__":
    result=build_sample_batch(Path("qa-sample-reels"))
    print(f"Rendered {len(result['reels'])} silent QA Reels. Publication eligible: {result['publish_eligible']}.")
