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
- duplicate and blank filter cleanup
- target URL generation
- fallback selection behavior when no explicit values are provided

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

The current state is best described as a documented foundation rather than a fully completed end-to-end automation flow. The next implementation phase would be to wire the remaining interactive UI steps for:
- movie selection
- theater filtering
- experience selection
- date selection
- preview-seat and timeslot looping
- screenshot capture with the requested file naming pattern

## How to use this codebase
1. Review the workflow notes in [documentation/workflow_notes.md](workflow_notes.md).
2. Adjust the values in [.env](../.env) if needed.
3. Run the probe script to verify the homepage before using the crawler.
4. Keep the documentation folder in sync as the workflow evolves.
