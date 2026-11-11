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
    # Reference-led composition: compact brand header, visible cricket photo hero,
    # story headline below the image, and a clean editorial footer.
    image = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 20, W-20, H-20), radius=34, outline=CYAN, width=4)
    draw.rounded_rectangle((42, 42, W-42, H-42), radius=26, outline=CYAN_DARK, width=2)
    draw.text((72, 64), "NEXZENCRICINFO", font=font(38, True), fill=WHITE)
    draw.text((72, 118), "NEXT GEN CRICKET  /  NEWS  •  RECORDS  •  INSIGHT", font=font(20, True), fill=MUTED)
    draw.line((72, 174, W-72, 174), fill=CYAN, width=3)

    # Story index mirrors the supplied reference template.
    draw.text((76, 208), "DAILY CRICKET", font=font(22, True), fill=CYAN)
    draw.text((330, 208), f"/  STORY {index:02d}  /  {total:02d}", font=font(22, True), fill=GOLD)
    for dot in range(total):
        x = W - 250 + dot * 38
        draw.ellipse((x, 214, x+13, 227), fill=GOLD if dot == index-1 else NAVY,
                     outline=GOLD if dot == index-1 else MUTED, width=2)

    # Prominent, real player photograph in a framed hero panel (not a faint full-canvas watermark).
    hero_box = (68, 260, W-68, 1035)
    draw.rounded_rectangle(hero_box, radius=18, fill=(8, 27, 62), outline=CYAN, width=3)
    background_value = scene.get("background_image", "")
    background_path = Path(background_value)
    if not background_path.is_absolute():
        background_path = Path(__file__).parent / background_path
    if background_path.is_file():
        with Image.open(background_path) as source_file:
            source = source_file.convert("RGB")
            box_w, box_h = hero_box[2]-hero_box[0]-16, hero_box[3]-hero_box[1]-16
            scale = max(box_w/source.width, box_h/source.height)
            resized = source.resize((int(source.width*scale), int(source.height*scale)), Image.Resampling.LANCZOS)
            left = max(0, (resized.width-box_w)//2)
            top = max(0, (resized.height-box_h)//2)
            photo = resized.crop((left, top, left+box_w, top+box_h))
        # Keep the photograph bright and recognizable; only a subtle lower fade protects text-free photo area.
        photo_overlay = Image.new("RGBA", photo.size, (0,0,0,0))
        overlay_draw = ImageDraw.Draw(photo_overlay)
        for yy in range(photo.height):
            alpha = int(4 + 22 * (yy / max(1, photo.height-1)))
            overlay_draw.line((0, yy, photo.width, yy), fill=(3,13,37,alpha))
        photo = Image.alpha_composite(photo.convert("RGBA"), photo_overlay).convert("RGB")
        image.paste(photo, (hero_box[0]+8, hero_box[1]+8))
    else:
        draw.text((112, 560), "PLAYER PHOTO NOT FOUND", font=font(34, True), fill=GOLD)
        draw.text((112, 620), "QA render must include the licensed image asset", font=font(22), fill=WHITE)

    draw = ImageDraw.Draw(image)
    # Thin inner frame and bottom fade of hero photograph.
    draw.rounded_rectangle(hero_box, radius=18, outline=CYAN, width=3)
    # Headline begins immediately under the photo, as in the user's example.
    eyebrow = scene["eyebrow"].upper()
    draw.text((82, 1070), eyebrow, font=font(24, True), fill=CYAN)
    title_font = font(59, True)
    title_lines = wrap(draw, scene["title"], title_font, W-164)
    y = 1122
    for line in title_lines[:2]:
        draw.text((82, y), line, font=title_font, fill=WHITE)
        y += 70
    body_y = y + 12
    for line in wrap(draw, scene["body"], font(34, True), W-164)[:2]:
        draw.text((84, body_y), line, font=font(34, True), fill=GOLD)
        body_y += 48
    note_y = body_y + 20
    for line in wrap(draw, scene.get("note", ""), font(21), W-164)[:2]:
        draw.text((84, note_y), line, font=font(21), fill=MUTED)
        note_y += 30

    # Compact branded footer; no empty decorative stat panel.
    footer_y = 1690
    draw.line((110, footer_y, 420, footer_y), fill=GOLD, width=2)
    draw.ellipse((525, footer_y-15, 555, footer_y+15), outline=GOLD, width=2)
    draw.line((660, footer_y, 970, footer_y), fill=GOLD, width=2)
    draw.text((72, 1750), "NEXZENCRICINFO  •  NEXT GEN CRICKET", font=font(18, True), fill=CYAN)
    draw.text((72, 1800), "QA SAMPLE ONLY  •  NOT APPROVED FOR PUBLICATION", font=font(17, True), fill=MUTED)
    draw.text((W-145, 1800), f"{index:02d}/{total:02d}", font=font(20, True), fill=WHITE)
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
