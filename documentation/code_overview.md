# Code overview

This document explains the main Python files that are currently present in the workspace and how they fit together.

## Repository entry points

### crawler.py
The main crawler workflow lives in [crawler.py](../crawler.py). It contains:
- configuration loading from the environment and the .env file
- filter normalization helpers for movies, theaters, and session types
- URL and filename helpers used by the workflow
- discovery logic that attempts to inspect the live Cineplex homepage
- browser automation helpers for navigation, selection, and screenshot output

Key responsibilities:
- load configuration from environment variables
- normalize filter values so the UI workflow uses clean, deduplicated labels
- build output paths for screenshots
- discover available filters from the live site when possible
- support later steps such as theater selection, experiences, dates, and preview-seat loops
- capture semantic seat-map metadata and filter screenshots by session, row, and adjacent-seat availability
- detect and dismiss sold-out preview modals, report the skipped session, and continue later timeslots
- provide reusable arrow-key single- and multi-select console prompts across the crawl and filtering stages
- guard empty multi-select submissions with an explicit select-all or go-back confirmation
- await console prompts on the crawler's existing asyncio loop so Questionary and Playwright can run together without nested event loops

### probe_cineplex.py
The lightweight probe script in [probe_cineplex.py](../probe_cineplex.py) is a smoke-test for the live Cineplex homepage. Its job is simpler than the crawler:
- launch a browser instance
- open the homepage
- print the page title
- look for visible labels such as Tickets, Showtimes, Theatres, and Theater
- report matching selectors

This script is useful as a basic reachability check and as a source of evidence for the documentation.

### tests/test_crawler.py
The regression tests in [tests/test_crawler.py](tests/test_crawler.py) validate core logic in the crawler without requiring a live browser session. They cover:
- configuration validation and path resolution
- filter normalization, date/time parsing, and output naming
- timestamped run-folder collision handling
- seat-type parsing and ordinary-seat classification
- schedule-period grouping and layout signatures
- aisle-safe adjacent-seat detection
- filtered/discarded file organization

## Configuration model
The crawler reads settings from the environment and from a local .env file. The most important values are:
- OUTPUT_DIR: root folder beneath which each run creates its own timestamp/movie/theatre screenshot directory
- DOCUMENTATION_DIR: folder for documentation artifacts
- MAX_DISTANCE_KM: theater distance threshold for filtering
- HEADLESS: whether the browser runs headless
- BROWSER_CHANNEL: browser channel to launch, such as msedge

## Current implementation status
The current codebase already includes:
- a working live-site probe
- a crawler module with helper functions and configuration handling
- regression tests for the core helpers
- a documentation folder for workflow notes and screenshots
- post-crawl organization into filtered and discarded subfolders using live seat metadata

The crawler implements the complete documented interactive flow: live discovery,
movie/theatre/experience/date selection, preview and timeslot traversal,
unobstructed screenshot capture, semantic seat-map collection, and optional
post-crawl filtering.

## How to use this codebase
1. Review the workflow notes in [documentation/workflow_notes.md](workflow_notes.md).
2. Adjust the values in [.env](../.env) if needed.
3. Run `python crawler.py` for the interactive workflow, or review the CLI options with `python crawler.py --help`.
4. Use the probe or opt-in live test when diagnosing live-site selector changes.
