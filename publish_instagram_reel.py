"""Publish a rendered Reel to Instagram using the Graph API."""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v26.0")
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"
STATE_FILE = Path("posted.json")


def request_json(method: str, path: str, *, data: dict | None = None, params: dict | None = None, label: str) -> dict:
    response = requests.request(method, f"{GRAPH_ROOT}/{path}", data=data, params=params, timeout=60)
    if not response.ok:
        try:
            detail = response.json().get("error", {})
            safe_detail = {key: detail.get(key) for key in ("message", "type", "code", "error_subcode") if key in detail}
        except ValueError:
            safe_detail = {"message": response.text[:500]}
        raise RuntimeError(f"{label} failed (HTTP {response.status_code}): {safe_detail}")
    return response.json()


def verify_account_access(user_id: str, token: str) -> None:
    account = request_json("GET", user_id, params={"fields": "id,username", "access_token": token}, label="Instagram account check")
    if str(account.get("id")) != str(user_id):
        raise RuntimeError("Instagram account check returned a different ID.")
    print(f"Instagram token diagnostic passed for @{account.get('username', 'unknown')}.")


def wait_until_finished(creation_id: str, token: str) -> None:
    for _ in range(36):
        result = request_json("GET", creation_id, params={"fields": "status_code", "access_token": token}, label="Check Reel processing")
        status = result.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError("Meta reported an error while processing the Reel.")
        time.sleep(5)
    raise TimeoutError("Reel processing did not finish within 180 seconds.")


def set_output(name: str, value: str) -> None:
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as output:
            output.write(f"{name}={value}\n")


def main() -> None:
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    user_id = os.environ["INSTAGRAM_USER_ID"]
    verify_account_access(user_id, token)

    slot = os.getenv("POST_SLOT", "").strip().lower()
    if slot not in {"morning", "evening", "night"}:
        raise RuntimeError(f"POST_SLOT must be morning/evening/night; received {slot!r}")
    today = datetime.now(IST).date().isoformat()
    key = f"{today}_{slot}_reel"

    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"published_dates": {}}
    reels = state.setdefault("published_reels", {})
    if key in reels:
        print(f"Reel already published for {key}; skipping duplicate.")
        set_output("status", "skipped")
        return

    video = Path("videos") / today / slot / "reel.mp4"
    if not video.is_file() or video.stat().st_size < 100_000:
        raise FileNotFoundError(f"Expected rendered Reel missing or invalid: {video}")

    draft_path = Path("drafts") / f"{today}_{slot}.md"
    if not draft_path.is_file():
        raise FileNotFoundError(f"Matching caption draft is missing: {draft_path}")
    draft = draft_path.read_text(encoding="utf-8")
    caption = draft.split("\n\n", 1)[1].split("\n\n## Source notes (not included in Instagram caption)", 1)[0].strip()
    if not caption:
        raise RuntimeError("Instagram Reel caption is empty.")

    source_section = draft.split("## Source notes (not included in Instagram caption)", 1)
    if len(source_section) > 1:
        for line in source_section[1].splitlines():
            match = re.match(r"\s*\d+\.\s+(.*?)\s+—\s+(https?://\S+)", line)
            if match and re.search(r"\b(?:pakistan(?:i|is)?|bangladesh(?:i|is)?)\b", match.group(1), re.IGNORECASE):
                raise RuntimeError("Reel publishing blocked: source notes contain restricted Pakistan/Bangladesh news.")

    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.getenv("GITHUB_REF_NAME", "main")
    video_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{video.as_posix()}"
    print(f"Using public GitHub raw video URL: {video_url}")

    container = request_json(
        "POST", f"{user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        label="Create Instagram Reel container",
    )
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError("Meta did not return a Reel container ID.")

    wait_until_finished(creation_id, token)
    published = request_json(
        "POST", f"{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        label="Publish Instagram Reel",
    )
    media_id = published.get("id")
    if not media_id:
        raise RuntimeError("Meta did not return a published Reel media ID.")

    reels[key] = media_id
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Published Instagram Reel {media_id} for {key}.")
    set_output("status", "published")


if __name__ == "__main__":
    main()
