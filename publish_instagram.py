"""Publish the generated six-slide carousel through the Instagram Graph API."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v22.0")
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"
STATE_FILE = Path("posted.json")


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
        response = requests.get(
            f"{GRAPH_ROOT}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
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
    today = datetime.now(IST).date().isoformat()

    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"published_dates": {}}
    if today in state.get("published_dates", {}):
        print(f"Already published for {today}; skipping duplicate.")
        return

    slide_dir = Path("images") / today
    slide_paths = [slide_dir / f"slide-{index}.jpg" for index in range(1, 7)]
    missing = [str(path) for path in slide_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Carousel slide(s) missing: {', '.join(missing)}")

    # Caption is the text between the draft heading and private source notes.
    draft_path = Path("drafts") / f"{today}.md"
    draft = draft_path.read_text(encoding="utf-8")
    parts = draft.split("\n\n", 1)
    if len(parts) != 2:
        raise RuntimeError(f"Unexpected draft format in {draft_path}")
    caption = parts[1].split("\n\n## Source notes (not included in Instagram caption)", 1)[0].strip()
    if not caption:
        raise RuntimeError("Instagram caption is empty after extracting the draft.")

    # Instagram fetches each public raw GitHub image URL to build the carousel.
    child_ids = []
    for index, path in enumerate(slide_paths, 1):
        image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path.as_posix()}"
        child = api_post(
            f"{user_id}/media",
            {
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": token,
            },
            f"Create carousel slide {index}",
        )
        child_id = child["id"]
        wait_until_finished(child_id, token, f"Carousel slide {index}")
        child_ids.append(child_id)
        print(f"Prepared carousel slide {index}/6.")

    carousel = api_post(
        f"{user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": token,
        },
        "Create carousel container",
    )
    carousel_id = carousel["id"]
    wait_until_finished(carousel_id, token, "Carousel container")

    published = api_post(
        f"{user_id}/media_publish",
        {"creation_id": carousel_id, "access_token": token},
        "Publish Instagram carousel",
    )
    media_id = published["id"]

    # Record only after Meta returns a successful publish response with a media ID.
    state.setdefault("published_dates", {})[today] = media_id
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Successfully published Instagram carousel {media_id} for {today}.")


if __name__ == "__main__":
    main()
