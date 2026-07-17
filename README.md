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

The crawler uses a consistent key-driven console menu for every interactive
choice. Use Up/Down to move, Space to toggle items in multi-select menus, `A`
to select or clear all items, and Enter to submit. This covers movie, theatres,
experiences, dates, post-crawl continue/stop, format/timeslot filtering, ticket
count, and acceptable rows.
Submitting any multi-select menu without choosing an item opens a confirmation:
choose `Select all` to use every option or `Go back` to reopen the list. `Go
back` is highlighted by default to prevent an accidental all-dates crawl.

Selections can also be supplied on the command line:

```powershell
python crawler.py `
  --movie "The Odyssey" `
  --theatre "Yonge-Eglinton" `
  --theatre "Vaughan" `
  --experience "IMAX" `
  --date "Tomorrow" `
  --headless
```

Useful safety and validation options include:

- `--dry-run`: complete discovery and selection without opening seat previews.
- `--max-screenshots N`: stop after `N` successful captures per theatre.
- Repeat `--theatre`, comma-separate names, or use `--theatre all` to process
  multiple nearby theatres.
- `--experience any`: do not restrict results by experience.
- `--all-dates` or `--date all`: process every date exposed by Cineplex.
- `--max-distance-km N`: override the configured theatre-distance threshold.
- `--headless` / `--no-headless`: override the `.env` browser mode.
- `--filter` / `--no-filter`: enter or skip post-crawl filtering without the
  initial yes/no question. The default asks once after all theatre crawls.

Run `python crawler.py --help` for the complete option list. Generated
screenshots go to `output/`; timestamped machine-readable run reports go to
`documentation/run_reports/`. Existing screenshots are never overwritten—a
numeric suffix is added when a filename already exists.

## Multiple theatres

The interactive setup order is movie, dates, theatres, then formats. Dates and
formats are chosen once, before crawling starts. The selected theatres are then
processed sequentially without further crawl prompts. Before each theatre after
the first, the crawler reloads Tickets and restores the movie so Cineplex cannot
carry filters across cinemas.

Each theatre's live date and format controls are rediscovered automatically and
matched to the global choices. Choices unavailable at one theatre are recorded
in that theatre's report and skipped there. If none of the selected dates or
formats are available, that theatre is marked `skipped-unavailable`; the crawler
never falls back to an unintended unfiltered crawl.

Each theatre receives its own
`YYYYMMDD-HHMMSS-MovieName-TheatreName` output directory. After every crawl has
finished, the crawler asks once whether to filter and asks once for the shared
ticket count. It then filters each theatre independently, asking for that
theatre's rows and timeslots so auditorium layouts and availability are never
mixed between cinemas.

The JSON report stores one entry per theatre under `theatre_runs`, plus
top-level aggregate captures, sold-out skips, and errors. Single-theatre runs
retain the previous top-level compatibility fields.

Each selected theatre creates a descriptive folder under the configured
`OUTPUT_DIR` using `YYYYMMDD-HHMMSS-MovieName-TheatreName`, for example
`output/20260717-031530-The_Odyssey-Cineplex_Yonge-Eglinton/`. If two otherwise
identical runs start within the same second, the later folder receives a numeric
suffix.

Screenshot filenames use
`Movie-Theatre-Format-YYYY_MM_DD_Weekday-HH_MM.png`, so files from the same
movie, theatre, and format sort chronologically by date and showtime. Times use
a zero-padded 24-hour clock: `2:00 PM` becomes `14_00`. For example:
`The_Odyssey-Cineplex_Cinemas_Vaughan-IMAX_70MM-2026_08_06_Thursday-23_00.png`.

Immediately before each capture, the crawler hides Cineplex's fixed `Copy Link`
/ `Buy Tickets` action sheet so it does not cover the seat map. This cleanup is
reapplied after every timeslot change.

The crawler also waits for Cineplex's popcorn seat-map loader and its dimming
overlay to remain absent before collecting seat data or taking a screenshot.
If the loader does not clear before the timeout, that capture fails instead of
saving an obstructed or stale image.

If Cineplex reports that a showtime is sold out, the crawler either skips its
already-disabled timeslot button before clicking or dismisses the modal with
`Change showtime`. The session is recorded under `skipped_sessions`, no
screenshot is created, and the remaining timeslots continue.

## Post-crawl filtering

After all successful theatre crawls, the crawler asks once whether to continue
with filtering. If accepted, it asks once for the number of side-by-side tickets
and then handles each theatre separately:

1. Detects distinct auditorium layouts and asks for acceptable rows once per
   format/layout combination.
2. Condenses captured sessions by format and consecutive date ranges that have
   the same schedule, then asks for a multi-selection of format/timeslot choices.
3. Keeps a screenshot when at least one selected row contains the requested
   number of adjacent available ordinary seats.
4. Moves matches to `filtered/` and all leftovers to `discarded/` inside the run
   directory.

Seat filtering uses semantic metadata captured from the live seat map, including
seat type, availability, row, number, and rendered position. This is more robust
than color-only image recognition. D-BOX, wheelchair, and companion positions
are excluded; Standard and sofa/recliner seats count. Consecutive numbering and
rendered spacing are both required, so seats separated by an aisle do not count
as side by side.

The run report records all filter choices, detected layouts and rows,
qualifying seat blocks, move reasons, and final screenshot paths.

Rows are selected from the same checkbox menu with Up/Down, Space, `A` for all,
and Enter.
When the crawler is run with redirected input instead of an interactive
terminal, it falls back to text prompts; that fallback accepts comma-separated
letters and ranges such as `A,B,C,F-J` or `AA-DD`.

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
