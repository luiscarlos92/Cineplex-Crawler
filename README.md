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
- `--filter` / `--no-filter`: enter or skip post-crawl filtering without the
  initial yes/no question. The default asks after every successful crawl.

Run `python crawler.py --help` for the complete option list. Generated
screenshots go to `output/`; timestamped machine-readable run reports go to
`documentation/run_reports/`. Existing screenshots are never overwritten—a
numeric suffix is added when a filename already exists.

Each invocation creates a descriptive folder under the configured `OUTPUT_DIR`
using `YYYYMMDD-HHMMSS-MovieName-TheatreName`, for example
`output/20260717-031530-The_Odyssey-Cineplex_Yonge-Eglinton/`. If two otherwise
identical runs start within the same second, the later folder receives a numeric
suffix.

Immediately before each capture, the crawler hides Cineplex's fixed `Copy Link`
/ `Buy Tickets` action sheet so it does not cover the seat map. This cleanup is
reapplied after every timeslot change.

## Post-crawl filtering

After a successful crawl, the crawler asks whether to continue with screenshot
filtering. If accepted, it:

1. Condenses captured sessions by format and consecutive date ranges that have
   the same schedule, then asks for a multi-selection of format/timeslot choices.
2. Asks how many side-by-side tickets are required.
3. Detects distinct auditorium layouts and asks for acceptable rows once per
   format/layout combination.
4. Keeps a screenshot when at least one selected row contains the requested
   number of adjacent available ordinary seats.
5. Moves matches to `filtered/` and all leftovers to `discarded/` inside the run
   directory.

Seat filtering uses semantic metadata captured from the live seat map, including
seat type, availability, row, number, and rendered position. This is more robust
than color-only image recognition. D-BOX, wheelchair, and companion positions
are excluded; Standard and sofa/recliner seats count. Consecutive numbering and
rendered spacing are both required, so seats separated by an aisle do not count
as side by side.

The run report records all filter choices, detected layouts and rows,
qualifying seat blocks, move reasons, and final screenshot paths.

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
