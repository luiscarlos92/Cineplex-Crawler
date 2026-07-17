# Development plan and current status

## Development plan

1. Keep the live-site probe as the first validation step.
2. Preserve the documented workflow in the repository so the browser flow is clear and repeatable.
3. Continue implementing the automation steps in the same order requested by the user:
   - open the homepage
   - navigate to tickets
   - discover and select movies
   - collect and filter theaters by distance
   - collect and apply experiences
   - collect dates and loop through them
   - iterate through preview seats and timeslots
   - capture screenshots with a deterministic naming pattern
4. Make the output directory configurable through .env.
5. Keep the documentation folder updated as evidence and screenshots are gathered.

## Current status

### Completed
- The workspace now contains a documentation-focused workflow runbook.
- The repository includes a live homepage probe script.
- The crawler module contains helper functions for configuration, filtering, URL generation, and output handling.
- Regression tests are present for the core helper logic.
- A .env file has been created with baseline configuration values.
- Screenshot evidence has been preserved under the documentation screenshots folder.
- Repository safety scaffolding is now present: `.gitignore`, `.env.example`, dependency metadata, and a setup README.
- Generated output and run reports have dedicated ignored locations; hand-written workflow documentation must never be overwritten by a crawler run.
- Configuration is validated and resolved relative to the repository; environment variables override `.env`, and geolocation requires a complete latitude/longitude pair.
- Movie, theatre, experience, and date discovery now use scoped live Tickets controls and structured Cineplex test IDs.
- Theatre options include live IDs, cities, and distances, are filtered by the configured maximum distance, and support interactive or CLI multi-selection.
- Selected theatres run sequentially with independent experience/date discovery, output folders, screenshot filtering, and report entries; Tickets is reset and the movie restored between theatres to prevent filter leakage.
- Key-driven terminal selections and optional command-line selections are implemented, including explicit `any` experiences and `all` dates. Interactive menus consistently use Up/Down, Space for multi-select, `A` to toggle all, and Enter to submit.
- Empty checkbox submissions open an explicit `Select all` / `Go back` confirmation for experiences, dates, sessions, and rows; `Go back` is the safe default.
- Questionary prompts use its asynchronous API on Playwright's existing event loop; a real keypress regression test protects against nested `asyncio.run()` failures.
- The nested date → preview group → overlay timeslot loop is implemented with deterministic collision-safe screenshot names.
- Screenshot date segments use `YYYY_MM_DD_Weekday`, preserving readable weekdays while sorting chronologically across months and years.
- Every execution writes a timestamped JSON report without modifying the hand-written workflow notes.
- Every invocation creates a unique `YYYYMMDD-HHMMSS-MovieName-TheatreName` screenshot subfolder beneath the configured output root.
- A bounded live run captured and visually verified two different timeslots from the same `UltraAVX + D-BOX` preview group.
- A bounded multi-theatre live run captured one preview each at Vaughan and Yonge-Eglinton after a clean Tickets/movie reset between theatres.
- Seat-preview captures hide Cineplex's fixed bottom action sheet after every preview load and timeslot rerender so it cannot cover seats or the legend.
- Seat-map readiness waits for Cineplex's popcorn loader and dimming overlay to remain absent, preventing stale or darkened screenshots during timeslot changes.
- Sold-out preview modals are detected during seat-map readiness, dismissed through `Change showtime`, reported as skipped sessions, and no longer block later timeslots.
- Each capture stores semantic seat-map metadata for accurate row, type, occupancy, and adjacency analysis.
- The post-crawl filter condenses timeslot schedules by format/date period, prompts for ticket count and rows per detected layout, then moves screenshots into `filtered/` or `discarded/`.
- Side-by-side detection excludes D-BOX and accessibility positions and checks both consecutive numbering and rendered spacing to avoid crossing aisles.
- The deterministic regression suite covers configuration, normalization, parsing, naming, collision handling, and selection matching; a live smoke test is opt-in.

### In progress
- A fully unbounded all-dates run has intentionally not been launched during development because it may create many screenshots. The bounded live runs prove the same traversal and timeslot-switching path.
- The local development configuration uses central Toronto coordinates, matching the saved workflow evidence; `.env.example` documents how to change them.

### Known constraints
- The live site structure may change and may require selectors to be adjusted.
- Movie, theatre, experience, and date availability is dynamic and depends on Cineplex, the configured location, and the current time.
- Cineplex injects its consent layer asynchronously; the crawler handles the current OneTrust implementation at initial navigation and after Tickets opens.
- A failed preview group stops the current theatre after recording the failure. Every subsequent selected theatre starts after Tickets is reloaded and the movie restored, avoiding both uncertain browser state and inherited filters.
- Accurate post-crawl filtering requires the seat metadata captured by this version; older screenshot-only runs are not automatically image-classified.

## Next recommended step
Run the crawler interactively with the desired real selections. Start with `--max-screenshots 2` for a bounded confirmation, then remove the limit when the output and selection set are correct.
