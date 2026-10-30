"""Publish carousel with per-slot duplicate protection and successful-post history."""
from __future__ import annotations

import json
import os
import re
import shutil
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


def verify_account_access(user_id: str, token: str) -> None:
    """Check the GitHub Actions token can read the configured Instagram account."""
    response = requests.get(
        f"{GRAPH_ROOT}/{user_id}",
        params={"fields": "id,username", "access_token": token},
        timeout=30,
    )
    if not response.ok:
        # Never print request params: they include the secret access token.
        try:
            detail = response.json().get("error", {})
            safe_detail = {key: detail.get(key) for key in ("message", "type", "code", "error_subcode") if key in detail}
        except ValueError:
            safe_detail = {"message": response.text[:500]}
        raise RuntimeError(f"Instagram token/account diagnostic failed: {safe_detail}")

    account = response.json()
    print(f"Instagram token diagnostic passed: id={account.get('id')}, username={account.get('username')}")
    if str(account.get("id")) != str(user_id):
        raise RuntimeError("Instagram token diagnostic returned an ID different from INSTAGRAM_USER_ID.")


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


def set_github_output(name: str, value: str) -> None:
    """Expose a publishing result to later GitHub Actions steps."""
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as output:
            output.write(f"{name}={value}\\n")


def main() -> None:
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    user_id = os.environ["INSTAGRAM_USER_ID"]
    verify_account_access(user_id, token)
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
        set_github_output("status", "skipped")
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
    # Instagram can report FINISHED before the carousel is actually publishable.
    # Retry only the transient "media not ready" response; do not recreate containers.
    publish_payload = {"creation_id": carousel["id"], "access_token": token}
    for attempt in range(1, 13):
        try:
            published = api_post(
                f"{user_id}/media_publish",
                publish_payload,
                "Publish Instagram carousel",
            )
            break
        except RuntimeError as exc:
            error_text = str(exc)
            is_not_ready = (
                '"code": 9007' in error_text
                and '"error_subcode": 2207027' in error_text
            )
            if not is_not_ready or attempt == 12:
                raise
            delay = min(5 * attempt, 30)
            print(
                f"Carousel is not publishable yet (attempt {attempt}/12); "
                f"waiting {delay}s before retry."
            )
            time.sleep(delay)
    media_id = published["id"]

    published_slots[slot_key] = media_id
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else {"stories": []}
    known_urls = {str(item.get("url", "")) for item in history.get("stories", [])}
    history.setdefault("stories", []).extend(story for story in stories if story["url"] not in known_urls)
    HISTORY_FILE.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")

    # Remove the source carousel assets only after Instagram confirms publication.
    shutil.rmtree(slide_dir)
    print(f"Removed local carousel images for {slot_key} after successful publication.")
    print(f"Successfully published Instagram carousel {media_id} for {slot_key}; recorded {len(stories)} stories.")
    set_github_output("status", "published")


if __name__ == "__main__":
    main()
