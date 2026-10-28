# NexZenCricInfo — AI Cricket News Draft Agent

A beginner-friendly first version of a daily cricket content assistant for **NexZenCricInfo** — "Where Next Gen Cricket Begins".

## What it does

- Collects cricket-related headlines from Google News RSS.
- Uses the OpenAI API to draft one Instagram caption in English.
- Saves the result as `drafts/YYYY-MM-DD.md`.
- Runs automatically every day at **8:30 AM India Standard Time (IST)** using GitHub Actions.
- Commits the draft back to this repository so it is easy to review.

## Important: this version does not publish to Instagram

The agent is deliberately **draft-only**. Review facts and sources before posting. Instagram publishing is not enabled or implemented yet; a personal Instagram account cannot be assumed to have the API setup required for automated publishing. Do not add Instagram tokens to this repository.

## Setup

### 1. Add your OpenAI API key as a GitHub secret

1. Open this repository on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Under **Secrets**, select **New repository secret**.
4. Name it `OPENAI_API_KEY` and paste your OpenAI API key.
5. Never paste the key into a source file or commit it. OpenAI API usage is billed separately from a ChatGPT subscription.

Optional: under **Variables**, add `OPENAI_MODEL` with value `gpt-4.1-mini`. If you skip this, the script uses that default.

### 2. Enable GitHub Actions

Open the **Actions** tab and enable workflows if GitHub asks. The workflow runs daily at 03:00 UTC (08:30 IST). GitHub scheduled jobs can sometimes start a little late, so this is a target time rather than a guaranteed exact minute.

### 3. Run a test manually

1. Open **Actions → Daily Cricket News Draft**.
2. Select **Run workflow**.
3. Wait for the run to finish, then open the `drafts/` folder on the `main` branch.

The first run requires a valid `OPENAI_API_KEY` secret. If no key is configured, the workflow will fail safely with an explanatory error.

## Run locally (optional)

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Set `OPENAI_API_KEY` in your shell environment, then run:

```bash
python cricket_agent.py
```

## Current limitations / next stage

- RSS results may include duplicate, stale, or low-quality headlines; review source links before publishing.
- The caption is AI-generated and can be wrong. Verify scores, dates, player names, and tournament status against reliable sources.
- This version generates text only: no image generation, image hosting, or Instagram publishing.
- The next stage can add branded post graphics and Meta's official Instagram publishing API after the Instagram account is set up as a Creator/Business account and the required permissions and credentials are configured.
