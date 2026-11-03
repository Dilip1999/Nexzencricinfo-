"""Create a vertical 9:16 Instagram Reel from the generated six-slide carousel.

Place an original or commercially licensed soundtrack at:
assets/audio/nexzencricinfo_theme.mp3
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

WIDTH, HEIGHT = 1080, 1920
FPS = 30
SLIDE_SECONDS = 4.0
TRANSITION_SECONDS = 0.35
SLIDE_COUNT = 6
AUDIO_DEFAULT = Path("assets/audio/nexzencricinfo_theme.mp3")


def build_vertical_frame(source: Path, destination: Path) -> None:
    """Show the complete 4:5 slide over a matching blurred 9:16 background."""
    with Image.open(source) as opened:
        slide = opened.convert("RGB")

    background = ImageOps.fit(
        slide, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS
    ).filter(ImageFilter.GaussianBlur(radius=34))
    background = Image.blend(background, Image.new("RGB", (WIDTH, HEIGHT), (5, 15, 42)), 0.58)

    # Preserve all slide text and graphics; the background fills the extra height.
    foreground = slide.copy()
    foreground.thumbnail((1024, 1280), Image.Resampling.LANCZOS)
    x = (WIDTH - foreground.width) // 2
    y = (HEIGHT - foreground.height) // 2

    canvas = background.convert("RGBA")
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x - 8, y - 8, x + foreground.width + 8, y + foreground.height + 8),
        radius=16, fill=(0, 0, 0, 170)
    )
    canvas = Image.alpha_composite(canvas, shadow)
    canvas.alpha_composite(foreground.convert("RGBA"), (x, y))
    ImageDraw.Draw(canvas).rounded_rectangle(
        (x - 2, y - 2, x + foreground.width + 2, y + foreground.height + 2),
        radius=10, outline=(0, 214, 232, 230), width=3
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, "JPEG", quality=94, optimize=True)


def build_filter_graph(frame_count: int) -> tuple[str, str, float]:
    filters = []
    clip_frames = int(FPS * SLIDE_SECONDS)
    for i in range(frame_count):
        filters.append(
            f"[{i}:v]scale={WIDTH}:{HEIGHT},"
            f"zoompan=z='min(zoom+0.00020,1.025)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={clip_frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
            "setsar=1,format=yuv420p,setpts=PTS-STARTPTS"
            f"[v{i}]"
        )

    current = "v0"
    elapsed = SLIDE_SECONDS - TRANSITION_SECONDS
    for i in range(1, frame_count):
        output = f"mix{i}"
        filters.append(
            f"[{current}][v{i}]xfade=transition=fade:"
            f"duration={TRANSITION_SECONDS}:offset={elapsed:.3f}[{output}]"
        )
        current = output
        elapsed += SLIDE_SECONDS - TRANSITION_SECONDS

    duration = frame_count * SLIDE_SECONDS - (frame_count - 1) * TRANSITION_SECONDS
    fade_start = max(0.0, duration - 1.5)
    filters.append(
        f"[{frame_count}:a]aresample=48000,volume=0.22,"
        "afade=t=in:st=0:d=0.6,"
        f"afade=t=out:st={fade_start:.3f}:d=1.5[aout]"
    )
    return ";".join(filters), current, duration


def create_reel(date: str, slot: str, audio_path: Path) -> Path:
    slide_dir = Path("images") / date / slot
    slides = [slide_dir / f"slide-{i}.jpg" for i in range(1, SLIDE_COUNT + 1)]
    missing = [str(path) for path in slides if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise FileNotFoundError("Cannot build Reel; missing slide(s): " + ", ".join(missing))
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise FileNotFoundError(
            f"Reel soundtrack not found: {audio_path}. Add an original or commercially "
            "licensed MP3 at this path before running Reels mode."
        )

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for Reel generation but was not found on PATH.")

    frame_dir = Path("reel_frames") / date / slot
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, slide in enumerate(slides, 1):
        frame = frame_dir / f"frame-{index}.jpg"
        build_vertical_frame(slide, frame)
        frames.append(frame)

    output = Path("videos") / date / slot / "reel.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    graph, final_video_label, duration = build_filter_graph(SLIDE_COUNT)

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for frame in frames:
        command.extend(["-loop", "1", "-framerate", str(FPS), "-t", str(SLIDE_SECONDS), "-i", str(frame)])
    command.extend(["-stream_loop", "-1", "-i", str(audio_path)])
    command.extend([
        "-filter_complex", graph,
        "-map", f"[{final_video_label}]",
        "-map", "[aout]",
        "-t", f"{duration:.3f}",
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart",
        str(output),
    ])

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "FFmpeg Reel rendering failed: " + (completed.stderr[-3000:] or "No FFmpeg error output.")
        )

    shutil.rmtree(frame_dir, ignore_errors=True)
    if not output.is_file() or output.stat().st_size < 100_000:
        raise RuntimeError("Reel MP4 was not created correctly or is unexpectedly small.")

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        check = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_name,codec_type,width,height",
             "-of", "default=noprint_wrappers=1", str(output)],
            capture_output=True, text=True
        )
        if check.returncode != 0:
            raise RuntimeError("Could not validate the generated Reel with ffprobe.")
        if "codec_name=h264" not in check.stdout or "codec_name=aac" not in check.stdout:
            raise RuntimeError("Reel must contain H.264 video and AAC audio.")
        if "width=1080" not in check.stdout or "height=1920" not in check.stdout:
            raise RuntimeError("Reel must be 1080x1920 vertical video.")

    print(f"Created Reel video: {output} ({output.stat().st_size:,} bytes)")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="India-local publication date YYYY-MM-DD")
    parser.add_argument("--slot", required=True, choices=("morning", "evening", "night"))
    parser.add_argument("--audio", type=Path, default=AUDIO_DEFAULT)
    args = parser.parse_args()
    create_reel(args.date, args.slot, args.audio)


if __name__ == "__main__":
    main()
