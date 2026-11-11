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
    source_url = "https://cricketdatabase.com/matches/2026-11-09-royal-desert-champions-v-united-tigers"
    source = "Cricket Database scorecard (match-level figures)"
    pending = "Scorecard review pending: innings extras do not reconcile in normalized data and listing format conflicts with competition label. Not approved for publication."
    # Each Reel follows a deliberate story arc: hook -> context -> evidence -> meaning -> CTA.
    # Voiceover is supplied for editorial review; this QA render remains silent.
    common = [
        {"eyebrow":"THE HOOK","title":"21 balls. 45 runs.","body":"A strike rate of 214.29","note":"FAKHAR ZAMAN  •  SCORECARD PERFORMANCE","voiceover":"Twenty-one balls. Forty-five runs. Fakhar Zaman's innings moved at a strike rate of 214.29."},
        {"eyebrow":"THE CONTEXT","title":"Not just a quick cameo","body":"45 from 21 deliveries","note":"One innings only — not a career or season statistic.","voiceover":"The headline is not just the total. It is how quickly those runs came: forty-five from twenty-one."},
        {"eyebrow":"THE COUNTERPOINT","title":"The ball had an answer","body":"Abbas Afridi: 3 for 10","note":"2 overs  •  Match figures listed by the scorecard","voiceover":"At the other end of the scorecard, Abbas Afridi delivered three wickets for ten runs in two overs."},
        {"eyebrow":"THE TAKEAWAY","title":"Two different forms of impact","body":"Batting tempo meets bowling control","note":"These are individual match figures; no unsupported cause or player-of-the-match claim is made.","voiceover":"One scorecard gives us two distinct performances: rapid scoring with the bat, and a three-wicket return with the ball."},
        {"eyebrow":"JOIN THE DEBATE","title":"Which number stands out?","body":"45 off 21  or  3 for 10?","note":"Source: Cricket Database scorecard  •  QA review only","voiceover":"Which performance stands out more to you? Forty-five off twenty-one, or three for ten? Tell us below."},
    ]
    battles = [
        {"eyebrow":"THE HOOK","title":"Same scorecard. Different tempo.","body":"Fakhar Zaman vs Waseem Muhammad","note":"A comparison of two listed innings — not a career rivalry.","voiceover":"Two batting contributions from one scorecard. The difference is the pace at which they scored."},
        {"eyebrow":"BATTER ONE","title":"Fakhar sets the pace","body":"45 runs from 21 balls","note":"Strike rate: 214.29","voiceover":"Fakhar Zaman scored forty-five from twenty-one deliveries, striking at 214.29."},
        {"eyebrow":"BATTER TWO","title":"Waseem builds his innings","body":"24 runs from 17 balls","note":"Strike rate: 141.18","voiceover":"Waseem Muhammad made twenty-four from seventeen, at a strike rate of 141.18."},
        {"eyebrow":"THE COMPARISON","title":"A 73.11-point gap","body":"214.29  vs  141.18","note":"Difference in listed innings strike rates; not a measure of overall player quality.","voiceover":"That is a difference of 73.11 strike-rate points in these innings. It describes this scorecard, not their overall ability."},
        {"eyebrow":"YOUR VERDICT","title":"Which innings would you pick?","body":"Explosive scoring or measured contribution?","note":"Source: Cricket Database scorecard  •  QA review only","voiceover":"Which innings would you choose for your team? Share your view."},
    ]
    analyst = [
        {"eyebrow":"THE HOOK","title":"84 chased. One wicket down.","body":"United Tigers finished in 7 overs","note":"The scorecard records a nine-wicket win.","voiceover":"An eighty-four run target. United Tigers reached it with one wicket down in seven overs."},
        {"eyebrow":"THE SCOREBOARD","title":"The chase in numbers","body":"84 for 1  •  7 overs","note":"Run rate from listed total and overs: 12.00 per over.","voiceover":"The listed chase finished at eighty-four for one after seven overs — twelve runs per over."},
        {"eyebrow":"THE RESULT","title":"A nine-wicket finish","body":"United Tigers won","note":"Result as recorded by the provider scorecard.","voiceover":"The recorded result: United Tigers won by nine wickets."},
        {"eyebrow":"WHAT THE DATA SAYS","title":"A dominant-looking finish","body":"Fast chase. One wicket lost.","note":"We cannot infer the tactical cause from the summary alone; innings detail needs verification.","voiceover":"The scoreboard shows a fast chase with one wicket lost. It does not, by itself, tell us which tactical choices made the difference."},
        {"eyebrow":"JOIN THE ANALYSIS","title":"What would you investigate next?","body":"Powerplay scoring  •  partnerships  •  boundaries","note":"Source: Cricket Database scorecard  •  QA review only","voiceover":"To explain why the chase was so quick, we'd next examine powerplay scoring, partnerships and boundary count. What would you look at first?"},
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
            storyboard += [f"## Scene {i}", f"**{scene['eyebrow']}**", f"**{scene['title']}**", scene["body"], scene.get("note",""), "", "**Voiceover:** "+scene.get("voiceover",""), ""]
        (output_dir/item["slug"]/"storyboard.md").write_text("\n".join(storyboard),encoding="utf-8")
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"sample-batch-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__ == "__main__":
    result=build_sample_batch(Path("qa-sample-reels"))
    print(f"Rendered {len(result['reels'])} silent QA Reels. Publication eligible: {result['publish_eligible']}.")
