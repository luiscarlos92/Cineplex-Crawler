# Cineplex workflow notes

This document preserves the documentation-only workflow for the Cineplex browser flow and the evidence already saved in the workspace.

## Current evidence
- The homepage flow is working.
- The live probe confirmed the page title "Cineplex.com | Movies, Showtimes, Tickets, Trailers" and visible navigation text for "Tickets" and "Theatres".
- Screenshots captured during the workflow are already stored in the workspace under the documentation screenshots folder.
- The automated workflow has been live-validated through movie, theatre, experience, and date selection.
- A bounded end-to-end run opened the seat-preview page, selected both the first and second timeslots, captured complete seat maps, and returned to Tickets without entering checkout.
- The crawler uses Cineplex's structured test IDs for the core workflow rather than scanning arbitrary body text.

## Detailed workflow

1. Open the homepage.
2. Navigate to the ticket/showtimes page.
   - Save the URL of the page that opens so the workflow can return to it later.
3. Open the Movies dropdown.
4. Extract all movie names from the page.
   - Scroll or use DOM extraction until the full list is collected.
5. Wait for manual movie selection using the arrow-key console menu.
   - For now, assume one movie is selected.
6. After the movie is chosen, select it in the filter menu by searching the textbox with the movie name.
7. Move to the theaters step.
8. Collect all theaters, including their name, city, and visible distance.
   - Filter to entries below the configured threshold.
   - Environment variable: MAX_DISTANCE_KM=50
9. Wait for manual theater selection.
   - Assume one theater is selected.
10. Click the chosen theater.
11. Open the filters panel.
12. Extract all available experiences.
13. Wait for manual experience selection.
   - Use Up/Down to navigate, Space to toggle multiple options, `A` to select or clear all options, and Enter to submit.
14. Apply the selected experiences.
15. Open the dates selector and export all visible dates.
   - Provide a visible `A` action that selects or clears ALL DATES and updates every checkbox.
16. Start the loop over the selected dates.
   - For each selected date:
     - Click the date.
     - Iterate through each Preview Seats group.
     - For each Preview Seats group, iterate through the available timeslots.
     - Click the timeslot.
     - If Cineplex displays the sold-out modal, click `Change showtime`, record the session as skipped, and continue to the next timeslot.
     - Capture a screenshot named using the pattern: Movie Name-Cinema Name-Format Name-Date-Timeslot
     - Continue until all timeslots are processed.
     - Return to the previous view and continue to the next Preview Seats group.
     - When all preview seats are done, return to the date list and continue to the next date.
17. End with a success or failure result and the output folder destination.
   - `OUTPUT_DIR` is the root; each invocation creates `YYYYMMDD-HHMMSS-MovieName-TheatreName` beneath it.
18. Ask whether to continue with post-crawl filtering.
   - If no, leave the captured screenshots in the run directory and finish.
   - If yes:
     - Group consecutive dates that share the same captured timeslot schedule for each format.
     - Present each format/timeslot/date-period combination as a separate arrow-key multi-select option.
     - Ask for the required number of side-by-side tickets using a single-select menu.
     - Detect distinct auditorium layouts from the captured seat metadata.
     - For each format/layout combination, display its detected rows and ask for a row multi-selection.
       - Use the same Up/Down, Space, `A` for all, and Enter checkbox interface.
       - A redirected-input fallback accepts row letters and inclusive ranges such as `A,B,C,F-J` or `AA-DD`.
     - Keep a screenshot if at least one selected row contains the requested number of adjacent available ordinary seats.
     - Move kept screenshots to `filtered/` and all other captures to `discarded/` within the run directory.

## Suggested environment variables
- MAX_DISTANCE_KM=50
- OUTPUT_DIR=output
- LATITUDE and LONGITUDE for the nearby-theatre origin
- HEADLESS=false
- BROWSER_CHANNEL=msedge

## Saved screenshot evidence
The following screenshots are already present in the workspace and should be treated as the captured evidence for the workflow:

- [documentation/user flow printscreens/image-1784252075712.png](documentation/user%20flow%20printscreens/image-1784252075712.png)
- [documentation/user flow printscreens/image-1784252097032.png](documentation/user%20flow%20printscreens/image-1784252097032.png)
- [documentation/user flow printscreens/image-1784252112016.png](documentation/user%20flow%20printscreens/image-1784252112016.png)
- [documentation/user flow printscreens/image-1784252129385.png](documentation/user%20flow%20printscreens/image-1784252129385.png)
- [documentation/user flow printscreens/image-1784252470558.png](documentation/user%20flow%20printscreens/image-1784252470558.png)
- [documentation/user flow printscreens/image-1784252500998.png](documentation/user%20flow%20printscreens/image-1784252500998.png)
- [documentation/user flow printscreens/image-1784252513969.png](documentation/user%20flow%20printscreens/image-1784252513969.png)
- [documentation/user flow printscreens/image-1784252677321.png](documentation/user%20flow%20printscreens/image-1784252677321.png)
- [documentation/user flow printscreens/image-1784252719633.png](documentation/user%20flow%20printscreens/image-1784252719633.png)
- [documentation/user flow printscreens/image-1784252751019.png](documentation/user%20flow%20printscreens/image-1784252751019.png)
- [documentation/user flow printscreens/image-1784252799671.png](documentation/user%20flow%20printscreens/image-1784252799671.png)
- [documentation/user flow printscreens/image-1784252814500.png](documentation/user%20flow%20printscreens/image-1784252814500.png)
- [documentation/user flow printscreens/image-1784252860927.png](documentation/user%20flow%20printscreens/image-1784252860927.png)
- [documentation/user flow printscreens/image-1784252873855.png](documentation/user%20flow%20printscreens/image-1784252873855.png)
- [documentation/user flow printscreens/image-1784252942694.png](documentation/user%20flow%20printscreens/image-1784252942694.png)
- [documentation/user flow printscreens/image-1784252996755.png](documentation/user%20flow%20printscreens/image-1784252996755.png)
- [documentation/user flow printscreens/image-1784253074772.png](documentation/user%20flow%20printscreens/image-1784253074772.png)
- [documentation/user flow printscreens/image-1784253188894.png](documentation/user%20flow%20printscreens/image-1784253188894.png)
- [documentation/user flow printscreens/image-1784253947231.png](documentation/user%20flow%20printscreens/image-1784253947231.png)

## Notes
- The workflow remains in the originally requested order, with manual selection points implemented as terminal menus.
- `--dry-run` validates discovery and selections without opening a seat preview.
- `--max-screenshots` allows a bounded end-to-end validation run.
- Each execution writes a timestamped JSON report under `documentation/run_reports/`, including status, selections, captures, and failures.
- Each execution writes screenshots into a new `YYYYMMDD-HHMMSS-MovieName-TheatreName` directory beneath `OUTPUT_DIR`; runs never share a screenshot directory.
- After capture, filtering is offered interactively. `--filter` accepts it without the initial question and `--no-filter` skips it.

## Implementation decisions

- The default user interaction is through consistent key-driven terminal menus: Up/Down navigates, Space toggles multi-select items, `A` selects or clears every item, and Enter submits. Optional command-line selections support repeatable unattended runs, while redirected input retains a text fallback.
- Interactive menus await Questionary on the crawler's existing asyncio loop. They must not call the synchronous prompt API, which would try to start a second event loop while Playwright is running.
- Nearby-theatre results use an explicit browser geolocation when `LATITUDE` and `LONGITUDE` are configured; both must be set together.
- The crawler stops at the seat-preview screen. It must not click `Buy Tickets`, select a seat, or enter checkout.
- Hand-written files in `documentation/` are preserved. Each execution writes a separate machine-readable report under `documentation/run_reports/`.
- Exploratory scripts and captured HTML/JSON remain in the workspace while the production workflow is completed.

## Live implementation validation

Validation performed on July 16, 2026 (America/Toronto):

1. Opened Tickets from the homepage and handled the delayed consent overlay.
2. Discovered and selected `The Odyssey` from the live movie drawer.
3. Collected structured theatre name, city, ID, and distance values, then selected `Cineplex Cinemas Yonge-Eglinton and VIP` at 1 km.
4. Verified both unfiltered (`any`) behavior and explicit `IMAX` filter submission.
5. Selected `Tomorrow — July 17, 2026` and discovered four live preview groups.
6. Opened the `UltraAVX + D-BOX` preview group and captured the 2:00 PM and 6:00 PM seat maps.
7. Verified that the second capture had the 6:00 PM timeslot selected and showed its distinct seat availability.
8. Exited through the preview close control; `Buy Tickets` was never clicked.

## Screenshot cleanup

- Cineplex places a fixed `Copy Link` / `Buy Tickets` action sheet over the bottom of the seat-preview viewport.
- Before every screenshot, the crawler hides the action sheet's full-width wrapper using the stable `bottom-sheet` test ID.
- The cleanup runs after entering each Preview Seats page and again after every timeslot switch because the live page may recreate the element during a rerender.
- Only the obstructing action sheet is hidden; the movie details, timeslot controls, seat map, legend, and availability state remain unchanged.
- Cineplex also displays a popcorn loading animation inside a full-page dimming overlay while a seat map changes.
- The crawler requires the popcorn loader to remain absent continuously before reading seats or capturing the page. A stuck loader fails the capture instead of producing a darkened screenshot.
- A sold-out modal takes precedence over the loader wait. The crawler dismisses it through `Change showtime`, skips the affected timeslot without a screenshot, and continues the preview loop.

## Seat availability filtering

- Every screenshot record includes a semantic snapshot of the live seat map: type, availability, row, seat number, and rendered coordinates.
- Ordinary seating includes Standard and sofa/recliner types. D-BOX, wheelchair, and companion positions are excluded from side-by-side calculations.
- Seats must have consecutive numbers and normal rendered spacing. This prevents adjacency from crossing an aisle.
- Auditorium layout signatures ignore occupancy, so different timeslots in the same room share one row prompt. A genuinely different seating layout produces a separate prompt.
- Schedule periods are derived from captured data rather than assumed. Consecutive dates with identical times are condensed; a schedule change starts a new period.
- The JSON run report records the selected sessions, ticket count, selected rows, qualifying seat blocks, kept/discarded reasons, and final paths.

