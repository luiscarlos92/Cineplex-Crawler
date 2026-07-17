# Cineplex seat-preview crawler

This project automates the documented Cineplex Tickets workflow and captures a
seat-preview screenshot for each selected date, experience, and timeslot. It
stops at the preview screen and never enters the seat-purchase flow.

See
[`documentation/workflow_notes.md`](documentation/workflow_notes.md) for the
target browser flow and [`documentation/development_plan.md`](documentation/development_plan.md)
for current status.

## Local setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install the project with `python -m pip install -e ".[test]"`.
3. Install a Playwright browser if Microsoft Edge is not already available:
   `python -m playwright install chromium`.
4. Copy `.env.example` to `.env` and adjust the location and browser settings.

## Usage

Start the interactive workflow with:

```powershell
python crawler.py
```

The crawler presents numbered menus for one movie, one theatre, multiple
experiences, and multiple dates. Leaving the experience prompt blank means no
experience filtering; entering `a` at the date prompt means all visible dates.

Selections can also be supplied on the command line:

```powershell
python crawler.py `
  --movie "The Odyssey" `
  --theatre "Yonge-Eglinton" `
  --experience "IMAX" `
  --date "Tomorrow" `
  --headless
```

Useful safety and validation options include:

- `--dry-run`: complete discovery and selection without opening seat previews.
- `--max-screenshots N`: stop after `N` successful captures.
- `--experience any`: do not restrict results by experience.
- `--all-dates` or `--date all`: process every date exposed by Cineplex.
- `--max-distance-km N`: override the configured theatre-distance threshold.
- `--headless` / `--no-headless`: override the `.env` browser mode.

Run `python crawler.py --help` for the complete option list. Generated
screenshots go to `output/`; timestamped machine-readable run reports go to
`documentation/run_reports/`. Existing screenshots are never overwritten—a
numeric suffix is added when a filename already exists.

Each invocation creates its own UTC-timestamped folder under the configured
`OUTPUT_DIR`, for example `output/20260717T031530Z/`. All screenshots from that
invocation are written to that folder. If two runs start within the same second,
the later folder receives a numeric suffix instead of reusing the first one.

Immediately before each capture, the crawler hides Cineplex's fixed `Copy Link`
/ `Buy Tickets` action sheet so it does not cover the seat map. This cleanup is
reapplied after every timeslot change.

After the editable install, `cineplex-crawler` can be used in place of
`python crawler.py`.

## Tests

Run the deterministic suite with:

```powershell
python -m pytest -q
```

The live-site smoke test is opt-in:

```powershell
$env:RUN_LIVE_TESTS="true"
python -m pytest -m live -q
```

The live test opens Cineplex and verifies the structured Tickets controls. It
does not enter a seat preview or produce screenshots.
