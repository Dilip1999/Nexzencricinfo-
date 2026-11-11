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
    image = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 20, W-20, H-20), radius=34, outline=CYAN, width=4)
    draw.rounded_rectangle((42, 42, W-42, H-42), radius=26, outline=CYAN_DARK, width=2)
    draw.text((72, 64), "NEXZENCRICINFO", font=font(38, True), fill=WHITE)
    draw.text((72, 118), "NEXT GEN CRICKET  /  NEWS  •  RECORDS  •  INSIGHT", font=font(20, True), fill=MUTED)
    draw.line((72, 174, W-72, 174), fill=CYAN, width=3)
    draw.text((76, 208), "DAILY CRICKET", font=font(22, True), fill=CYAN)
    draw.text((330, 208), f"/  STORY {index:02d}  /  {total:02d}", font=font(22, True), fill=GOLD)
    for dot in range(total):
        x = W - 250 + dot * 38
        draw.ellipse((x, 214, x+13, 227), fill=GOLD if dot == index-1 else NAVY,
                     outline=GOLD if dot == index-1 else MUTED, width=2)

    # Preserve the complete story-specific player photo: contain, never crop the face.
    hero_box = (68, 260, W-68, 1015)
    draw.rounded_rectangle(hero_box, radius=18, fill=(8, 27, 62), outline=CYAN, width=3)
    background_path = Path(scene.get("background_image", ""))
    if not background_path.is_absolute():
        background_path = Path(__file__).parent / background_path
    if background_path.is_file():
        with Image.open(background_path) as source_file:
            source = source_file.convert("RGB")
            box_w, box_h = hero_box[2]-hero_box[0]-20, hero_box[3]-hero_box[1]-20
            source.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
            px = hero_box[0] + 10 + (box_w-source.width)//2
            py = hero_box[1] + 10 + (box_h-source.height)//2
            image.paste(source, (px, py))
    else:
        draw.text((112, 560), "PLAYER PHOTO NOT FOUND", font=font(34, True), fill=GOLD)
        draw.text((112, 620), "QA render must include the selected story image", font=font(22), fill=WHITE)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(hero_box, radius=18, outline=CYAN, width=3)

    draw.text((82, 1040), scene["eyebrow"].upper(), font=font(24, True), fill=CYAN)
    title_font = font(55, True)
    title_lines = wrap(draw, scene["title"], title_font, W-164)
    y = 1088
    for line in title_lines[:2]:
        draw.text((82, y), line, font=title_font, fill=WHITE)
        y += 62
    body_y = y + 2
    for line in wrap(draw, scene["body"], font(30, True), W-164)[:2]:
        draw.text((84, body_y), line, font=font(30, True), fill=GOLD)
        body_y += 40
    note_y = body_y + 6
    for line in wrap(draw, scene.get("note", ""), font(18), W-164)[:1]:
        draw.text((84, note_y), line, font=font(18), fill=MUTED)

    # Bottom section displays only explicit, source-grounded statistics.
    stats = scene.get("stats", [])
    if stats:
        panel_top, panel_bottom = 1450, 1685
        draw.rounded_rectangle((76, panel_top, W-76, panel_bottom), radius=22,
                               fill=(8, 27, 62), outline=CYAN, width=2)
        cell_width = (W-176) / min(3, len(stats))
        for stat_index, stat in enumerate(stats[:3]):
            x0 = 88 + stat_index*cell_width
            if stat_index:
                draw.line((int(x0-10), panel_top+25, int(x0-10), panel_bottom-25),
                          fill=CYAN_DARK, width=2)
            draw.text((int(x0+12), panel_top+38), str(stat["value"]),
                      font=font(43, True), fill=GOLD)
            labels = wrap(draw, str(stat["label"]).upper(), font(16, True), int(cell_width-30))
            for label_index, label in enumerate(labels[:2]):
                draw.text((int(x0+12), panel_top+105+label_index*22), label,
                          font=font(16, True), fill=CYAN)

    draw.text((72, 1740), "NEXZENCRICINFO  •  NEXT GEN CRICKET", font=font(18, True), fill=CYAN)
    draw.text((72, 1790), "QA SAMPLE ONLY  •  NOT APPROVED FOR PUBLICATION",
              font=font(17, True), fill=MUTED)
    draw.text((W-145, 1790), f"{index:02d}/{total:02d}", font=font(20, True), fill=WHITE)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95)

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
    player_image = fixture["featured_player_image"]
    player_asset = player_image["asset"]
    scenes = [
        {"background_image":player_asset,"eyebrow":"THE HOOK","title":"Seven short of a hundred.","body":"Virat Kohli  •  93 off 91 balls","note":"8 fours  •  1 six  •  Strike rate 102.20","stats":[{"value":"93","label":"Runs"},{"value":"91","label":"Balls"},{"value":"102.20","label":"Strike rate"}],"spotlight_value":"93","spotlight_label":"Runs from 91 balls","voiceover":"Seven runs short of a hundred. Virat Kohli made 93 from 91 balls against New Zealand in the first ODI."},
        {"background_image":player_asset,"eyebrow":"THE SUPPORTING STORY","title":"The innings around him","body":"Gill 56  •  Iyer 49","note":"Two more major contributions on India scorecard.","stats":[{"value":"56","label":"Gill runs"},{"value":"49","label":"Iyer runs"},{"value":"105","label":"Combined runs"}],"voiceover":"Kohli wasn't the only contributor. Shubman Gill scored 56, while Shreyas Iyer added 49."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"THE SCOREBOARD","title":"India reached 306 for 6","body":"49 overs  •  India won by 4 wickets","note":"Score and result exactly as shown in the supplied screenshot.","stats":[{"value":"306/6","label":"India total"},{"value":"49","label":"Overs"},{"value":"4 wkts","label":"Win margin"}],"spotlight_value":"306/6","spotlight_label":"India innings total","voiceover":"India's innings finished at 306 for six in 49 overs, and the scorecard records a four-wicket win."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"THE DETAIL","title":"A century that stayed just out of reach","body":"93 runs  •  8 boundaries for four  •  1 six","note":"Kohli was dismissed, caught by Michael Bracewell off Kyle Jamieson, according to the visible scorecard.","voiceover":"Kohli's 93 included eight fours and one six. The scorecard shows him caught by Michael Bracewell off Kyle Jamieson."},
        {"background_image":"assets/players/virat_kohli.jpg","eyebrow":"JOIN THE DEBATE","title":"Was 93 the defining innings?","body":"Kohli 93  •  Gill 56  •  Iyer 49","note":"Based only on the visible India innings. First-innings context is not shown.","voiceover":"Which innings stood out most to you — Kohli's 93, Gill's 56, or Iyer's 49? Tell us in the comments."}
    ]
    item = {"slug":"india-nz-kohli-93-story","title":"India vs New Zealand: Kohli's 93", "pillar":"stats", "scenes":scenes}
    manifest = {
        "status":"qa_sample_only",
        "publish_eligible":False,
        "audio":"silent review render; voiceover script included; soundtrack and narration not yet added",
        "source":{"name":source,"match":fixture["match"],"venue":fixture["venue"]},"player_image":player_image,
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
        "**Limitations:** "+limitations, "", "**Featured player background:** "+player_image["player"]+" — "+player_image["attribution"]+", "+player_image["license"]+". "+player_image["note"]+" Source: "+player_image["source_url"], ""
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
