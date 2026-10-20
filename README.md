# JKantic | Codex + Resend scheduling starter

This is a **local starter**, not a deployed automation. Nothing is sent until you explicitly approve rows and run with `--commit`. Existing Resend schedules are not changed.

## What it does

- Loads individually personalized emails from `queue.csv`.
- Schedules **only** rows with `status=approved`.
- Uses the Resend API, not brittle browser clicking.
- Runs in preview mode by default.
- Schedules weekdays at 11:00 South Africa time, with two-minute spacing.
- Logs attempts and Resend IDs to reduce duplicate scheduling.

## Quick setup in Codex or Terminal

1. Open this folder in Codex and ask it to help run these commands.
2. Install Python 3.10+ and dependencies: `python3 -m pip install -r requirements.txt`.
3. Set your Resend API key in your terminal: `export RESEND_API_KEY='your_key'`. **Do not paste the key into ChatGPT, Codex prompts, or commit it to Git.** Prefer Codex's secure secret/environment support if available.
4. Review `queue.csv` and verify recipient, business fit, dates and content. Change only approved messages' `status` from `draft` to `approved`.
5. Preview: `python3 outreach.py --limit 5`.
6. Schedule ONE approved email as a test: `python3 outreach.py --commit --limit 1`.
7. Verify the scheduled email in Resend. Once satisfied, use `python3 outreach.py --commit --limit 20` for subsequent approved messages.

## Important limits

- This script is not an always-on scheduler. It schedules future deliveries in Resend when run. To automate future daily batches, run it via a scheduler (e.g. Codex-created GitHub Actions with secrets or a hosted job). Do not use GitHub Actions until secrets, approvals, and deduplication are reviewed.
- The CSV is an import of previously drafted outreach. All imported messages are **draft**; none are approved by default. Proposed dates from older drafts are not used.
- A `scheduled_log.jsonl` entry with `state=attempted` means you must check Resend manually before retrying after an error. This intentionally prevents accidental duplicates.
- Resend sender domain must be verified and API key must have sending access. Sending and scheduling remain subject to Resend policies and applicable direct-marketing rules.
- Notion sync is **not yet connected**. The first version uses a CSV queue to avoid more account setup. Codex can add Notion sync later.
