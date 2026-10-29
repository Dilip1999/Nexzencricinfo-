"""Publish the generated daily PNG through the Instagram Graph API."""
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

    image_path = Path("images") / f"{today}.png"
    if not image_path.exists():
        raise FileNotFoundError(f"Generated image not found: {image_path}")
    # Instagram fetches this URL remotely. The repository must be public.
    image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{image_path.as_posix()}"

    draft_path = Path("drafts") / f"{today}.md"
    draft = draft_path.read_text(encoding="utf-8")
    sections = draft.split("\n\n", 2)
    caption = sections[2] if len(sections) > 2 else draft
    caption = caption.split("\n\n## Articles collected", 1)[0]
    caption = caption.strip()

    # Create media container.
    created = requests.post(
        f"{GRAPH_ROOT}/{user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    created.raise_for_status()
    creation_id = created.json().get("id")
    if not creation_id:
        raise RuntimeError(f"Instagram container response did not include an id: {created.text}")

    # Wait for Instagram to finish fetching and processing the image.
    for _ in range(18):
        status_response = requests.get(
            f"{GRAPH_ROOT}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        status_response.raise_for_status()
        status = status_response.json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram media processing failed: {status_response.text}")
        time.sleep(5)
    else:
        raise TimeoutError("Instagram did not finish processing the media container within 90 seconds.")

    # Publish the finished container.
    published = requests.post(
        f"{GRAPH_ROOT}/{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    published.raise_for_status()
    media_id = published.json().get("id")
    if not media_id:
        raise RuntimeError(f"Instagram publish response did not include a media id: {published.text}")

    state.setdefault("published_dates", {})[today] = media_id
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Successfully published Instagram media {media_id} for {today}.")


if __name__ == "__main__":
    main()
