# evr-news

A small bot that keeps a Slack channel up to date on AI in education.

- **Every weekday, about 08:07 London time:** a brief catch-up: one lead story (headline + one sentence), up to 2 quick hits and up to 2 "also seen" links. Monday's covers the weekend.
- **Quiet day:** if nothing relevant came in since the last post, nothing is posted.
- **Weekends:** new items are scored and kept for Monday; nothing is posted.

## How it works

1. Reads the public feeds and sitemaps in [`sources.json`](sources.json) (DfE, Ofqual, Ofsted, DSIT, ICO, European Commission, BBC Education, Wonkhe, HEPI, Hechinger, EdSurge, OpenAI, Google, DeepMind, Anthropic, Stanford SCALE).
2. Skips anything already seen ([`state/seen.json`](state/seen.json), committed back by the workflow).
3. **Claude Sonnet** scores each new item for relevance and impact.
4. **Claude Opus** picks the lead and quick hits from the top 10 and writes them, from the fetched pages only.
5. Code inserts titles, links and dates. Each summary must include a verbatim quote that the code finds in the page; if it doesn't, the summary is dropped and only the title and link are posted.

Sources behind bot protection (for example EEF, OECD, Jisc, Schools Week) are left out on purpose: we don't work around it.

## Setup

Repository secrets (Settings → Secrets and variables → Actions):

| Secret | What |
|---|---|
| `ANTHROPIC_API_KEY` | API key with a monthly spend limit (suggested US$10) |
| `SLACK_WEBHOOK_URL` | Incoming webhook for the target channel |

Until both secrets are set, scheduled runs do nothing and change no state. A manual run with `dry_run` on needs only `ANTHROPIC_API_KEY` and prints the message in the log.

Before enabling the secrets, make sure branch rules on `main` let GitHub Actions push (the state commit).

## Running it

- **Manually:** Actions → news → Run workflow. `dry_run` is on by default (prints the message, changes no state).
- **Locally:**

  ```bash
  python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
  .venv/bin/python -m pytest -q tests
  .venv/bin/python bot/news.py --fetch-only          # test the sources, no API calls
  ANTHROPIC_API_KEY=... .venv/bin/python bot/news.py --dry-run --force
  ```

## Notes

- The schedule fires at 07:07 and 08:07 UTC; the bot only works on the first run at or after 08:00 London time, so it is right in both GMT and BST.
- The daily state commit keeps the repository active, so GitHub should not disable the schedule after 60 days of inactivity (UNKNOWN whether bot commits count; if the schedule stops, re-enable it in the Actions tab).
- Cost: one Sonnet triage call per day and one Opus call per weekday catch-up; expected well under US$1 per run.
