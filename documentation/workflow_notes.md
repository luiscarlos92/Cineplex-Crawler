# Cineplex workflow notes

This document preserves the documentation-only workflow for the Cineplex browser flow and the evidence already saved in the workspace.

## Current evidence
- The homepage flow is working.
- The live probe confirmed the page title "Cineplex.com | Movies, Showtimes, Tickets, Trailers" and visible navigation text for "Tickets" and "Theatres".
- Screenshots captured during the workflow are already stored in the workspace under the documentation screenshots folder.
- The automated workflow has been live-validated through movie, theatre, experience, and date selection.
- A bounded end-to-end run opened the seat-preview page, selected both the first and second timeslots, captured complete seat maps, and returned to Tickets without entering checkout.
- A bounded multi-theatre run reset Tickets between cinemas and captured one seat map each for Vaughan and Yonge-Eglinton without mixing filters or output directories.
- A live UI probe confirmed that Cineplex exposes its 28-date selector before any theatre is chosen, allowing dates to be selected globally in the requested prompt order.
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
7. Open the date selector and export all dates visible for the selected movie.
8. Wait for one global date multi-selection.
   - The selection is made before theatres so it is not bound to one cinema.
   - Provide a visible `A` action that selects or clears all dates.
9. Move to the theaters step and collect all theaters, including their name, city, and visible distance.
   - Filter to entries below the configured threshold.
   - Environment variable: MAX_DISTANCE_KM=50
10. Wait for manual theatre multi-selection.
   - Support one or more theatres, plus the visible toggle-all action.
11. Open the global filters panel and wait for one format/experience multi-selection.
   - Use Up/Down to navigate, Space to toggle multiple options, `A` to select or clear all options, and Enter to submit.
   - If Enter is pressed with nothing selected, ask whether to `Select all` or `Go back`; default to `Go back`.
12. Start the automatic loop over selected theatres. Do not prompt during this crawl loop.
13. Click the current theatre, rediscover its live format options, and map the global format selection to them.
   - Record formats unavailable at this theatre.
   - If no selected format is available, mark the theatre `skipped-unavailable`; never crawl it without the requested filter.
14. Apply the mapped formats, rediscover the theatre's live dates, and map the global date selection to them.
   - Record dates unavailable at this theatre.
   - If no selected date is available, mark the theatre `skipped-unavailable`.
15. Start the automatic loop over the mapped dates.
   - For each selected date:
     - Click the date.
     - Iterate through each Preview Seats group.
     - For each Preview Seats group, iterate through the available timeslots.
     - Click the timeslot.
     - If the timeslot button is already disabled and marked Sold Out, record it as skipped without attempting a click.
     - If Cineplex displays the sold-out modal, click `Change showtime`, record the session as skipped, and continue to the next timeslot.
     - Capture a screenshot named using the pattern: Movie Name-Cinema Name-Format Name-YYYY_MM_DD_Weekday-HH_MM.
       - Parse Cineplex's display date and place the zero-padded year, month, and day first so filename sorting is chronological.
       - Convert AM/PM showtimes to a zero-padded 24-hour clock so sessions on the same date also sort chronologically.
     - Continue until all timeslots are processed.
     - Return to the previous view and continue to the next Preview Seats group.
     - When all preview seats are done, return to the date list and continue to the next date.
16. End the current theatre with a success, skipped, or failure result and its output folder destination.
   - `OUTPUT_DIR` is the root; each selected theatre creates `YYYYMMDD-HHMMSS-MovieName-TheatreName` beneath it.
17. Return to clean movie-selection state and repeat steps 13-16 for the next selected theatre.
   - Reload Tickets and restore the movie so Cineplex cannot carry filters between cinemas.
   - If one theatre fails, record its error and still attempt the clean reset for the next theatre.
18. After every theatre crawl has finished, ask once whether to continue with post-crawl filtering.
   - If no, leave every captured screenshot in its theatre run directory.
   - If yes, ask once for the required number of side-by-side tickets. This value is shared by all theatres.
19. Filter each theatre independently.
   - Detect distinct auditorium layouts from that theatre's captured seat metadata.
   - For each format/layout combination, display its detected rows and ask for a row multi-selection.
       - Use the same Up/Down, Space, `A` for all, and Enter checkbox interface.
       - An empty submission must ask whether to select every row or return to the row list.
       - A redirected-input fallback accepts row letters and inclusive ranges such as `A,B,C,F-J` or `AA-DD`.
   - Group consecutive dates that share the same captured timeslot schedule for each format.
   - Present each format/timeslot/date-period combination as a separate arrow-key multi-select option.
   - Keep a screenshot if at least one selected row contains the shared ticket count in adjacent available ordinary seats.
   - Move kept screenshots to `filtered/` and all other captures to `discarded/` within that theatre's run directory.

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
- `--max-screenshots` allows a bounded end-to-end validation run per theatre.
- Each execution writes a timestamped JSON report under `documentation/run_reports/`, including status, selections, captures, and failures.
- Each selected theatre writes screenshots into its own `YYYYMMDD-HHMMSS-MovieName-TheatreName` directory beneath `OUTPUT_DIR`; theatres never share a screenshot directory.
- After all theatre captures, filtering is offered once. `--filter` accepts it and `--no-filter` skips it without that question.

## Implementation decisions

- The default user interaction is through consistent key-driven terminal menus: Up/Down navigates, Space toggles multi-select items, `A` selects or clears every item, and Enter submits. Optional command-line selections support repeatable unattended runs, while redirected input retains a text fallback.
- Empty multi-select submissions are never accepted silently. A follow-up offers `Select all` or `Go back`, with `Go back` as the safe default.
- Interactive menus await Questionary on the crawler's existing asyncio loop. They must not call the synchronous prompt API, which would try to start a second event loop while Playwright is running.
- Nearby-theatre results use an explicit browser geolocation when `LATITUDE` and `LONGITUDE` are configured; both must be set together.
- Date and experience selections are global prompts before crawling. Each theatre then rediscovers its live options and maps those choices automatically. Tickets is reloaded and the movie restored before each subsequent theatre, and post-crawl seat filtering never combines different theatres.
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

Multi-theatre validation performed on July 17, 2026 (America/Toronto):

1. Selected `The Odyssey` once and resolved both `Cineplex Cinemas Vaughan` and `Cineplex Cinemas Yonge-Eglinton and VIP` from repeatable CLI theatre values.
2. Completed a two-theatre dry run with independent experience and date discovery.
3. Completed a bounded live run with `--max-screenshots 1`, capturing one `UltraAVX + D-BOX` preview at each theatre.
4. Reloaded Tickets and restored the movie between theatres; the second theatre began without the first theatre's experience-filter state.
5. Created separate timestamp/movie/theatre output directories and a report containing two `theatre_runs` entries.

Global-prompt validation performed on July 17, 2026 (America/Toronto):

1. Confirmed the live 28-date list is available immediately after movie selection and before theatre selection.
2. Chose `Today` and `IMAX` once, then completed a non-capturing dry run for Vaughan and Yonge-Eglinton.
3. Rediscovered and mapped the same date and format independently at both theatres without additional prompts.
4. Reset Tickets and restored the movie between theatres; both theatre reports completed with one mapped date and one mapped experience.

## Screenshot cleanup

- Cineplex places a fixed `Copy Link` / `Buy Tickets` action sheet over the bottom of the seat-preview viewport.
- Before every screenshot, the crawler hides the action sheet's full-width wrapper using the stable `bottom-sheet` test ID.
- The cleanup runs after entering each Preview Seats page and again after every timeslot switch because the live page may recreate the element during a rerender.
- Only the obstructing action sheet is hidden; the movie details, timeslot controls, seat map, legend, and availability state remain unchanged.
- Cineplex also displays a popcorn loading animation inside a full-page dimming overlay while a seat map changes.
- The crawler requires the popcorn loader to remain absent continuously before reading seats or capturing the page. A stuck loader fails the capture instead of producing a darkened screenshot.
- A sold-out modal takes precedence over the loader wait. The crawler dismisses it through `Change showtime`, skips the affected timeslot without a screenshot, and continues the preview loop.
- A disabled Sold Out timeslot is detected before `click()`, avoiding Playwright's enabled-element timeout and immediately continuing the preview loop.

## Seat availability filtering

- Every screenshot record includes a semantic snapshot of the live seat map: type, availability, row, seat number, and rendered coordinates.
- Ordinary seating includes Standard and sofa/recliner types. D-BOX, wheelchair, and companion positions are excluded from side-by-side calculations.
- Seats must have consecutive numbers and normal rendered spacing. This prevents adjacency from crossing an aisle.
- Auditorium layout signatures ignore occupancy, so different timeslots in the same room share one row prompt. A genuinely different seating layout produces a separate prompt.
- Schedule periods are derived from captured data rather than assumed. Consecutive dates with identical times are condensed; a schedule change starts a new period.
- The JSON run report records the selected sessions, ticket count, selected rows, qualifying seat blocks, kept/discarded reasons, and final paths.

