"""Publish carousel with per-slot duplicate protection and successful-post history."""
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
# Keep this aligned with the Graph API version configured and tested in Meta Graph API Explorer.
GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v26.0")
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"
STATE_FILE = Path("posted.json")
HISTORY_FILE = Path("content_history.json")


def api_post(path: str, data: dict, what: str) -> dict:
    response = requests.post(f"{GRAPH_ROOT}/{path}", data=data, timeout=60)
    if not response.ok:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:2000]
        raise RuntimeError(f"{what} failed (HTTP {response.status_code}): {detail}")
    result = response.json()
    if not result.get("id"):
        raise RuntimeError(f"{what} response did not include an id: {result}")
    return result


def wait_until_finished(creation_id: str, token: str, what: str) -> None:
    for _ in range(24):
        response = requests.get(f"{GRAPH_ROOT}/{creation_id}",
            params={"fields": "status_code", "access_token": token}, timeout=30)
        response.raise_for_status()
        status = response.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"{what} processing failed: {response.text}")
        time.sleep(5)
    raise TimeoutError(f"{what} did not finish processing within 120 seconds.")


def main() -> None:
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    user_id = os.environ["INSTAGRAM_USER_ID"]
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.getenv("GITHUB_REF_NAME", "main")
    slot = os.getenv("POST_SLOT", "").strip().lower()
    if slot not in {"morning", "evening", "night"}:
        raise RuntimeError(f"POST_SLOT must be morning/evening/night; received {slot!r}")
    today = datetime.now(IST).date().isoformat()
    slot_key = f"{today}_{slot}"

    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"published_dates": {}}
    published_slots = state.setdefault("published_dates", {})
    if slot_key in published_slots:
        print(f"Already published slot {slot_key}; skipping duplicate.")
        return

    slide_dir = Path("images") / today / slot
    slide_paths = [slide_dir / f"slide-{i}.jpg" for i in range(1, 7)]
    missing = [str(p) for p in slide_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Carousel slide(s) missing: {', '.join(missing)}")

    draft = (Path("drafts") / f"{today}_{slot}.md").read_text(encoding="utf-8")
    caption = draft.split("\n\n", 1)[1].split("\n\n## Source notes (not included in Instagram caption)", 1)[0].strip()
    if not caption:
        raise RuntimeError("Instagram caption is empty after extracting the draft.")

    source_section = draft.split("## Source notes (not included in Instagram caption)", 1)[1]
    stories = []
    for line in source_section.splitlines():
        match = re.match(r"\s*\d+\.\s+(.*?)\s+—\s+(https?://\S+)", line)
        if match:
            stories.append({"title": match.group(1).strip(), "url": match.group(2).strip(),
                            "slot": slot, "date": today})

    child_ids = []
    for index, path in enumerate(slide_paths, 1):
        image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path.as_posix()}"
        child = api_post(f"{user_id}/media",
            {"image_url": image_url, "is_carousel_item": "true", "access_token": token},
            f"Create carousel slide {index}")
        wait_until_finished(child["id"], token, f"Carousel slide {index}")
        child_ids.append(child["id"])
        print(f"Prepared carousel slide {index}/6.")

    carousel = api_post(f"{user_id}/media",
        {"media_type": "CAROUSEL", "children": ",".join(child_ids),
         "caption": caption, "access_token": token}, "Create carousel container")
    wait_until_finished(carousel["id"], token, "Carousel container")
    published = api_post(f"{user_id}/media_publish",
        {"creation_id": carousel["id"], "access_token": token}, "Publish Instagram carousel")
    media_id = published["id"]

    published_slots[slot_key] = media_id
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else {"stories": []}
    known_urls = {str(item.get("url", "")) for item in history.get("stories", [])}
    history.setdefault("stories", []).extend(story for story in stories if story["url"] not in known_urls)
    HISTORY_FILE.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(f"Successfully published Instagram carousel {media_id} for {slot_key}; recorded {len(stories)} stories.")


if __name__ == "__main__":
    main()
