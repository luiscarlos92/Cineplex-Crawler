from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, replace
from datetime import date as calendar_date
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

try:
    import questionary
except ImportError:  # The text fallback keeps the module usable before dependencies are installed.
    questionary = None

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, async_playwright


ROOT = Path(__file__).resolve().parent
HOME_URL = "https://www.cineplex.com/"


@dataclass(frozen=True)
class Config:
    output_dir: Path
    documentation_dir: Path
    max_distance_km: float
    headless: bool
    browser_channel: str | None
    locale: str
    timezone_id: str
    latitude: float | None
    longitude: float | None
    geolocation_accuracy_meters: float

    @property
    def geolocation(self) -> dict[str, float] | None:
        if self.latitude is None or self.longitude is None:
            return None
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.geolocation_accuracy_meters,
        }

    @property
    def run_reports_dir(self) -> Path:
        return self.documentation_dir / "run_reports"


@dataclass(frozen=True)
class MovieOption:
    title: str
    button_name: str


@dataclass(frozen=True)
class TheatreOption:
    theatre_id: str
    name: str
    city: str
    distance_km: float

    @property
    def display_name(self) -> str:
        city = f" — {self.city}" if self.city else ""
        return f"{self.name}{city} — {self.distance_km:g} km"


@dataclass(frozen=True)
class ExperienceOption:
    label: str
    aria_label: str


@dataclass(frozen=True)
class DateOption:
    test_id: str
    label: str


@dataclass(frozen=True)
class PreviewGroup:
    index: int
    format_name: str
    times: tuple[str, ...]


@dataclass(frozen=True)
class TimeslotChoice:
    format_name: str
    timeslot: str
    period_labels: tuple[str, ...]
    capture_indexes: tuple[int, ...]

    @property
    def display_name(self) -> str:
        period = self.period_labels[0]
        if len(self.period_labels) > 1:
            period = f"{self.period_labels[0]} → {self.period_labels[-1]}"
        return f"{self.format_name} — {self.timeslot} — {period}"


@dataclass(frozen=True)
class LayoutGroup:
    signature: str
    format_name: str
    rows: tuple[str, ...]
    date_labels: tuple[str, ...]
    capture_indexes: tuple[int, ...]

    @property
    def display_name(self) -> str:
        dates = self.date_labels[0]
        if len(self.date_labels) > 1:
            dates = f"{self.date_labels[0]} → {self.date_labels[-1]}"
        return f"{self.format_name} — {dates} — rows {', '.join(self.rows)}"


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().upper()] = value.strip().strip('"').strip("'")
    return values


def _setting(file_values: dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key, file_values.get(key, default)).strip()


def _parse_bool(value: str, key: str) -> bool:
    normalized = value.casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be true or false, not {value!r}")


def _optional_float(value: str, key: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a number, not {value!r}") from exc


def _rooted_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def load_config() -> Config:
    values = _read_env_file(ROOT / ".env")
    latitude = _optional_float(_setting(values, "LATITUDE"), "LATITUDE")
    longitude = _optional_float(_setting(values, "LONGITUDE"), "LONGITUDE")
    if (latitude is None) != (longitude is None):
        raise ValueError("LATITUDE and LONGITUDE must either both be set or both be blank")
    if latitude is not None and not -90 <= latitude <= 90:
        raise ValueError("LATITUDE must be between -90 and 90")
    if longitude is not None and not -180 <= longitude <= 180:
        raise ValueError("LONGITUDE must be between -180 and 180")

    return Config(
        output_dir=_rooted_path(_setting(values, "OUTPUT_DIR", "output")),
        documentation_dir=_rooted_path(_setting(values, "DOCUMENTATION_DIR", "documentation")),
        max_distance_km=float(_setting(values, "MAX_DISTANCE_KM", "50")),
        headless=_parse_bool(_setting(values, "HEADLESS", "false"), "HEADLESS"),
        browser_channel=_setting(values, "BROWSER_CHANNEL", "msedge") or None,
        locale=_setting(values, "LOCALE", "en-CA"),
        timezone_id=_setting(values, "TIMEZONE_ID", "America/Toronto"),
        latitude=latitude,
        longitude=longitude,
        geolocation_accuracy_meters=float(_setting(values, "GEOLOCATION_ACCURACY_METERS", "100")),
    )


def normalize_filter_options(values: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        cleaned = re.sub(r"\s+", " ", str(value).strip())
        cleaned = cleaned.replace("â€“", "-").replace("â€”", "-")
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def safe_filename(value: object, max_length: int = 60) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._-")
    return (safe or "item")[:max_length].rstrip("._-") or "item"


def build_target_url(movie: str, theater: str = "", session_type: str = "") -> str:
    del theater, session_type
    slug = re.sub(r"[^a-z0-9]+", "-", movie.casefold()).strip("-") or "movie"
    return f"https://www.cineplex.com/en/movie/{slug}"


def resolve_selection(selected: Sequence[str], defaults: Sequence[str]) -> Sequence[str]:
    return selected or defaults


def parse_distance(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*km\b", value, flags=re.I)
    return float(match.group(1)) if match else None


def clean_movie_label(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"\s+Advance tickets?$", "", cleaned, flags=re.I).strip()


def extract_time(value: str) -> str:
    match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", value, flags=re.I)
    return re.sub(r"\s+", " ", match.group(0)).upper() if match else value.strip()


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for suffix in range(2, 10_000):
        candidate = path.with_name(f"{path.stem}_{suffix}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find a free output filename for {path.name}")


def create_run_output_dir(
    output_root: Path,
    started_at: datetime,
    movie_name: str,
    theatre_name: str,
) -> Path:
    """Create one descriptive, collision-safe folder for a crawler invocation."""
    timestamp = (started_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    folder_name = "-".join(
        (
            timestamp.strftime("%Y%m%d-%H%M%S"),
            safe_filename(movie_name, 45),
            safe_filename(theatre_name, 55),
        )
    )
    run_dir = unique_path(output_root / folder_name)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir
def build_output_path(
    movie: str,
    theatre: str,
    session_type: str,
    date: str = "date",
    timeslot: str = "time",
    output_dir: Path | None = None,
) -> Path:
    directory = output_dir or (ROOT / "output")
    parts = [
        safe_filename(movie, 45),
        safe_filename(theatre, 55),
        safe_filename(session_type, 40),
        safe_filename(date, 35),
        safe_filename(timeslot, 15),
    ]
    return directory / ("-".join(parts) + ".png")


def _match_named_choice(query: str, options: Sequence[object], label_getter) -> object:
    normalized = query.strip().casefold()
    exact = [option for option in options if label_getter(option).casefold() == normalized]
    if len(exact) == 1:
        return exact[0]
    partial = [option for option in options if normalized in label_getter(option).casefold()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise ValueError(f"No option matches {query!r}")
    matches = ", ".join(label_getter(option) for option in partial[:8])
    raise ValueError(f"{query!r} is ambiguous; matching options: {matches}")


def _console_menu_available() -> bool:
    """Return whether full-screen key-driven prompts are safe in this process."""
    return bool(
        questionary is not None
        and getattr(sys.stdin, "isatty", lambda: False)()
        and getattr(sys.stdout, "isatty", lambda: False)()
    )


def _ask_console_question(question):
    answer = question.ask()
    if answer is None:
        raise KeyboardInterrupt
    return answer


def prompt_single_choice(options: Sequence[object], label: str, label_getter=str) -> object:
    if not options:
        raise RuntimeError(f"No options were discovered for {label.lower()}")
    if _console_menu_available():
        choices = [
            questionary.Choice(title=str(label_getter(option)), value=option, shortcut_key=False)
            for option in options
        ]
        return _ask_console_question(
            questionary.select(
                label,
                choices=choices,
                pointer=">",
                instruction="(Up/Down to move, Enter to select)",
                use_shortcuts=False,
                use_jk_keys=False,
            )
        )

    print(f"\n{label}")
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {label_getter(option)}")
    while True:
        raw = input("Enter a number (or 'q' to quit): ").strip().casefold()
        if raw in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("Please enter one of the displayed numbers.")


def prompt_multi_choice(
    options: Sequence[object],
    label: str,
    label_getter=str,
    *,
    blank_means_none: bool = False,
) -> list[object]:
    if not options:
        return []
    if _console_menu_available():
        choices = [
            questionary.Choice(title=str(label_getter(option)), value=option, shortcut_key=False)
            for option in options
        ]
        validation = (
            (lambda selected: True)
            if blank_means_none
            else (lambda selected: bool(selected) or "Select at least one item.")
        )
        return list(
            _ask_console_question(
                questionary.checkbox(
                    label,
                    choices=choices,
                    pointer=">",
                    instruction="(Up/Down to move, Space to toggle, Enter to submit)",
                    use_jk_keys=False,
                    validate=validation,
                )
            )
        )

    print(f"\n{label}")
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {label_getter(option)}")
    hint = "Enter comma-separated numbers, 'a' for all"
    if blank_means_none:
        hint += ", or leave blank for no filtering"
    while True:
        raw = input(f"{hint} (or 'q' to quit): ").strip().casefold()
        if raw in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        if not raw and blank_means_none:
            return []
        if raw in {"a", "all"}:
            return list(options)
        indexes: list[int] = []
        valid = True
        for token in raw.split(","):
            token = token.strip()
            if not token.isdigit() or not 1 <= int(token) <= len(options):
                valid = False
                break
            index = int(token) - 1
            if index not in indexes:
                indexes.append(index)
        if valid and indexes:
            return [options[index] for index in indexes]
        print("Please enter one or more displayed numbers.")


def parse_row_selection(raw: str, available_rows: Sequence[str]) -> list[str]:
    normalized_rows = {row.casefold(): row for row in available_rows}
    value = raw.strip()
    if value.casefold() == "all":
        return list(available_rows)
    if not value:
        raise ValueError("Enter at least one row")

    selected: list[str] = []
    for token in value.split(","):
        token = token.strip()
        range_match = re.fullmatch(r"([A-Za-z]+)\s*-\s*([A-Za-z]+)", token)
        if range_match:
            start_key = range_match.group(1).casefold()
            end_key = range_match.group(2).casefold()
            if start_key not in normalized_rows or end_key not in normalized_rows:
                raise ValueError(f"Unknown row range: {token}")
            start_row = normalized_rows[start_key]
            end_row = normalized_rows[end_key]
            start_index = available_rows.index(start_row)
            end_index = available_rows.index(end_row)
            if start_index > end_index:
                raise ValueError(f"Row range must follow the displayed order: {token}")
            for row in available_rows[start_index : end_index + 1]:
                if row not in selected:
                    selected.append(row)
            continue

        key = token.casefold()
        if key not in normalized_rows:
            raise ValueError(f"Unknown row: {token or '(blank)'}")
        row = normalized_rows[key]
        if row not in selected:
            selected.append(row)
    return selected


def prompt_row_selection(available_rows: Sequence[str], label: str) -> list[str]:
    if not available_rows:
        return []
    if _console_menu_available():
        return list(
            _ask_console_question(
                questionary.checkbox(
                    label,
                    choices=[
                        questionary.Choice(title=row, value=row, shortcut_key=False)
                        for row in available_rows
                    ],
                    pointer=">",
                    instruction="(Up/Down to move, Space to toggle, Enter to submit)",
                    use_jk_keys=False,
                    validate=lambda selected: bool(selected) or "Select at least one row.",
                )
            )
        )

    print(f"\n{label}")
    print(f"Available rows: {', '.join(available_rows)}")
    while True:
        raw = input("Enter rows (example A,B,C,F-J), 'all' for every row (or 'q' to quit): ").strip()
        if raw.casefold() in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        try:
            return parse_row_selection(raw, available_rows)
        except ValueError as exc:
            print(f"{exc}. Please use displayed row letters and ranges.")


def prompt_yes_no(question: str, *, default: bool = False) -> bool:
    if _console_menu_available():
        choices = ["Yes", "No"]
        answer = _ask_console_question(
            questionary.select(
                question,
                choices=choices,
                default="Yes" if default else "No",
                pointer=">",
                instruction="(Up/Down to move, Enter to select)",
                use_shortcuts=False,
                use_jk_keys=False,
            )
        )
        return answer == "Yes"

    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{question} {suffix}: ").strip().casefold()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        if raw in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        print("Please answer yes or no.")


def prompt_positive_int(question: str) -> int:
    if _console_menu_available():
        choices = [
            questionary.Choice(
                title=f"{count} ticket{'s' if count != 1 else ''}",
                value=count,
                shortcut_key=False,
            )
            for count in range(1, 51)
        ]
        return int(
            _ask_console_question(
                questionary.select(
                    question,
                    choices=choices,
                    default=choices[1],
                    pointer=">",
                    instruction="(Up/Down to move, Enter to select)",
                    use_shortcuts=False,
                    use_jk_keys=False,
                )
            )
        )

    while True:
        raw = input(f"{question} (or 'q' to quit): ").strip().casefold()
        if raw in {"q", "quit", "exit"}:
            raise KeyboardInterrupt
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Please enter a whole number greater than zero.")


EXCLUDED_ORDINARY_SEAT_TYPES = {"dbox", "companion", "wheelchair"}


def parse_seat_test_id(test_id: str) -> dict[str, object] | None:
    match = re.fullmatch(
        r"(?P<seat_type>.+)-(?P<status>available|occupied)-seat-(?P<row>[A-Z]+)(?P<number>\d+)",
        test_id,
        flags=re.I,
    )
    if not match:
        return None
    return {
        "seat_type": match.group("seat_type"),
        "status": match.group("status").casefold(),
        "row": match.group("row").upper(),
        "number": int(match.group("number")),
        "code": f"{match.group('row').upper()}{int(match.group('number'))}",
    }


def is_ordinary_seat(seat: dict[str, object]) -> bool:
    seat_type = str(seat.get("seat_type", "")).casefold()
    return bool(seat_type) and seat_type not in EXCLUDED_ORDINARY_SEAT_TYPES


def _date_from_capture(capture: dict[str, object]) -> calendar_date | None:
    iso_value = capture.get("date_iso")
    if iso_value:
        try:
            return calendar_date.fromisoformat(str(iso_value))
        except ValueError:
            pass
    label = str(capture.get("date", ""))
    match = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),\s+(\d{4})\b",
        label,
        flags=re.I,
    )
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%B %d, %Y").date()
    except ValueError:
        return None


def date_iso_from_label(label: str) -> str | None:
    parsed = _date_from_capture({"date": label})
    return parsed.isoformat() if parsed else None


def _timeslot_sort_key(value: str) -> tuple[int, str]:
    try:
        parsed = datetime.strptime(value.strip().upper(), "%I:%M %p")
        return parsed.hour * 60 + parsed.minute, value
    except ValueError:
        return 24 * 60, value


def build_timeslot_choices(captures: Sequence[dict[str, object]]) -> list[TimeslotChoice]:
    by_format: dict[str, dict[str, dict[str, object]]] = {}
    for index, capture in enumerate(captures):
        format_name = str(capture.get("format", "Unknown format"))
        date_label = str(capture.get("date", "Unknown date"))
        timeslot = str(capture.get("timeslot", "Unknown time"))
        date_entry = by_format.setdefault(format_name, {}).setdefault(
            date_label,
            {"date": _date_from_capture(capture), "times": {}},
        )
        times = date_entry["times"]
        assert isinstance(times, dict)
        times.setdefault(timeslot, []).append(index)

    choices: list[TimeslotChoice] = []
    for format_name in sorted(by_format, key=str.casefold):
        date_entries = list(by_format[format_name].items())
        date_entries.sort(key=lambda item: (item[1]["date"] is None, item[1]["date"] or calendar_date.max))
        periods: list[list[tuple[str, dict[str, object]]]] = []
        for label, entry in date_entries:
            signature = tuple(sorted(entry["times"], key=_timeslot_sort_key))
            if not periods:
                periods.append([(label, entry)])
                continue
            _, previous_entry = periods[-1][-1]
            previous_signature = tuple(sorted(previous_entry["times"], key=_timeslot_sort_key))
            previous_date = previous_entry["date"]
            current_date = entry["date"]
            consecutive = (
                previous_date is None
                or current_date is None
                or current_date == previous_date + timedelta(days=1)
            )
            if signature == previous_signature and consecutive:
                periods[-1].append((label, entry))
            else:
                periods.append([(label, entry)])

        for period in periods:
            period_labels = tuple(label for label, _ in period)
            signature = tuple(sorted(period[0][1]["times"], key=_timeslot_sort_key))
            for timeslot in signature:
                capture_indexes: list[int] = []
                for _, entry in period:
                    times = entry["times"]
                    assert isinstance(times, dict)
                    capture_indexes.extend(times.get(timeslot, []))
                choices.append(
                    TimeslotChoice(
                        format_name=format_name,
                        timeslot=timeslot,
                        period_labels=period_labels,
                        capture_indexes=tuple(capture_indexes),
                    )
                )
    return choices


def seat_layout_signature(seats: Sequence[dict[str, object]]) -> str:
    row_min_x: dict[str, float] = {}
    for seat in seats:
        row = str(seat.get("row", ""))
        x = float(seat.get("x", 0))
        row_min_x[row] = min(x, row_min_x.get(row, x))
    layout = sorted(
        (
            str(seat.get("seat_type", "")),
            str(seat.get("row", "")),
            int(seat.get("number", 0)),
            round(float(seat.get("x", 0)) - row_min_x.get(str(seat.get("row", "")), 0), 1),
            round(float(seat.get("width", 0)), 1),
        )
        for seat in seats
    )
    return hashlib.sha1(json.dumps(layout, separators=(",", ":")).encode("utf-8")).hexdigest()[:12]


def detected_ordinary_rows(seats: Sequence[dict[str, object]]) -> tuple[str, ...]:
    row_y: dict[str, float] = {}
    for seat in seats:
        if not is_ordinary_seat(seat):
            continue
        row = str(seat.get("row", ""))
        y = float(seat.get("y", 0))
        if row:
            row_y[row] = min(y, row_y.get(row, y))
    return tuple(sorted(row_y, key=lambda row: (row_y[row], row)))


def build_layout_groups(
    captures: Sequence[dict[str, object]], eligible_indexes: set[int]
) -> list[LayoutGroup]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for index in sorted(eligible_indexes):
        capture = captures[index]
        seats = capture.get("seats")
        if not isinstance(seats, list) or not seats:
            continue
        signature = str(capture.get("layout_signature") or seat_layout_signature(seats))
        format_name = str(capture.get("format", "Unknown format"))
        key = (format_name, signature)
        entry = grouped.setdefault(
            key,
            {
                "rows": detected_ordinary_rows(seats),
                "dates": [],
                "indexes": [],
            },
        )
        date_label = str(capture.get("date", "Unknown date"))
        dates = entry["dates"]
        indexes = entry["indexes"]
        assert isinstance(dates, list) and isinstance(indexes, list)
        if date_label not in dates:
            dates.append(date_label)
        indexes.append(index)

    return [
        LayoutGroup(
            signature=signature,
            format_name=format_name,
            rows=tuple(entry["rows"]),
            date_labels=tuple(entry["dates"]),
            capture_indexes=tuple(entry["indexes"]),
        )
        for (format_name, signature), entry in grouped.items()
    ]


def find_adjacent_seat_blocks(
    seats: Sequence[dict[str, object]], selected_rows: set[str], ticket_count: int
) -> list[dict[str, object]]:
    by_row: dict[str, list[dict[str, object]]] = {}
    for seat in seats:
        row = str(seat.get("row", ""))
        if row in selected_rows and is_ordinary_seat(seat):
            by_row.setdefault(row, []).append(seat)

    qualifying: list[dict[str, object]] = []
    for row in selected_rows:
        row_seats = sorted(by_row.get(row, []), key=lambda seat: float(seat.get("x", 0)))
        run: list[dict[str, object]] = []

        def finish_run() -> None:
            if len(run) >= ticket_count:
                qualifying.append(
                    {
                        "row": row,
                        "seats": [str(seat.get("code", "")) for seat in run],
                        "available_count": len(run),
                    }
                )

        for seat in row_seats:
            if str(seat.get("status", "")).casefold() != "available":
                finish_run()
                run = []
                continue
            if run:
                previous = run[-1]
                number_is_adjacent = abs(int(seat.get("number", 0)) - int(previous.get("number", 0))) == 1
                rendered_gap = float(seat.get("x", 0)) - float(previous.get("x", 0))
                width_threshold = max(float(seat.get("width", 0)), float(previous.get("width", 0))) * 1.75
                if not number_is_adjacent or rendered_gap > width_threshold:
                    finish_run()
                    run = []
            run.append(seat)
        finish_run()
    return qualifying


async def _dismiss_cookie_dialog(page: Page) -> None:
    accept = page.locator("#onetrust-accept-btn-handler")
    try:
        await accept.wait_for(state="visible", timeout=4_000)
        await accept.click(timeout=5_000, force=True)
    except PlaywrightTimeoutError:
        pass


async def open_tickets(page: Page) -> str:
    if not page.url.startswith(HOME_URL):
        await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45_000)
    if page.url == "about:blank":
        await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45_000)
    await _dismiss_cookie_dialog(page)
    dialog = page.get_by_role("dialog", name="Tickets")
    if not await dialog.count() or not await dialog.first.is_visible():
        await page.get_by_role("button", name="Tickets", exact=True).click(timeout=15_000)
    await page.get_by_test_id("select-movie").wait_for(state="visible", timeout=30_000)
    # OneTrust can appear late, after the Tickets drawer is already visible.
    await _dismiss_cookie_dialog(page)
    return page.url


async def collect_movie_options(page: Page) -> list[MovieOption]:
    await page.get_by_test_id("select-movie").click()
    dialog = page.get_by_role("dialog", name="Select movie")
    await dialog.get_by_placeholder("Search movies").wait_for(state="visible", timeout=15_000)

    ignored = {"back", "see all movies"}
    options: list[MovieOption] = []
    for _ in range(20):
        options = []
        seen: set[str] = set()
        buttons = dialog.get_by_role("button")
        for index in range(await buttons.count()):
            button = buttons.nth(index)
            if not await button.is_visible():
                continue
            raw = re.sub(r"\s+", " ", (await button.inner_text()).strip())
            title = clean_movie_label(raw)
            key = title.casefold()
            if not title or key in ignored or key in seen:
                continue
            if any(marker in key for marker in ("preview seats", "theatres near me")):
                continue
            if parse_distance(title) is not None or re.fullmatch(r"\d{1,2}:\d{2}\s*(?:am|pm)", title, re.I):
                continue
            seen.add(key)
            options.append(MovieOption(title=title, button_name=raw))
        if options:
            break
        await page.wait_for_timeout(500)
    if not options:
        raise RuntimeError("The Select movie dialog opened, but no movie choices were found")
    return options


async def select_movie(page: Page, option: MovieOption) -> None:
    dialog = page.get_by_role("dialog", name="Select movie")
    search = dialog.get_by_placeholder("Search movies")
    await search.fill(option.title)
    await page.wait_for_timeout(400)
    candidates = dialog.get_by_role("button")
    for index in range(await candidates.count()):
        candidate = candidates.nth(index)
        if not await candidate.is_visible():
            continue
        raw = re.sub(r"\s+", " ", (await candidate.inner_text()).strip())
        if clean_movie_label(raw).casefold() == option.title.casefold():
            await candidate.click()
            await page.get_by_test_id("select-theatre").wait_for(state="visible", timeout=20_000)
            return
    raise RuntimeError(f"Movie disappeared from the selection dialog: {option.title}")


async def collect_theatre_options(page: Page, max_distance_km: float) -> list[TheatreOption]:
    await page.get_by_test_id("select-theatre").click()
    dialog = page.get_by_role("dialog", name="Select a theatre")
    await dialog.get_by_placeholder("Search by theatres or cities").wait_for(state="visible", timeout=15_000)

    option_locator = dialog.locator('[data-testid^="theatre-id-"]')
    previous_count = -1
    stable_rounds = 0
    for _ in range(20):
        count = await option_locator.count()
        if count == 0:
            await page.wait_for_timeout(500)
            continue
        if count == previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        if stable_rounds >= 2:
            break
        previous_count = count
        await option_locator.last.scroll_into_view_if_needed()
        await page.wait_for_timeout(350)

    options: list[TheatreOption] = []
    for index in range(await option_locator.count()):
        locator = option_locator.nth(index)
        test_id = await locator.get_attribute("data-testid") or ""
        theatre_id = test_id.removeprefix("theatre-id-")
        name = re.sub(r"\s+", " ", (await locator.inner_text()).strip())
        distance_locator = dialog.get_by_test_id(f"distance-theatreId-{theatre_id}")
        city_locator = dialog.get_by_test_id(f"city-theatre-Id-{theatre_id}")
        distance = parse_distance(await distance_locator.inner_text()) if await distance_locator.count() else None
        city = re.sub(r"\s+", " ", (await city_locator.inner_text()).strip()) if await city_locator.count() else ""
        if distance is None or distance > max_distance_km:
            continue
        options.append(TheatreOption(theatre_id, name, city, distance))
    options.sort(key=lambda option: (option.distance_km, option.name.casefold()))
    if not options:
        raise RuntimeError(f"No theatres were found within {max_distance_km:g} km")
    return options


async def select_theatre(page: Page, option: TheatreOption) -> None:
    await page.get_by_role("dialog", name="Select a theatre").get_by_test_id(
        f"theatre-id-{option.theatre_id}"
    ).click()
    await page.get_by_test_id("select-filters").wait_for(state="visible", timeout=20_000)


async def collect_experience_options(page: Page) -> list[ExperienceOption]:
    await page.get_by_test_id("select-filters").click()
    dialog = page.get_by_role("dialog", name="Filter")
    await dialog.get_by_role("button", name="Apply", exact=True).wait_for(state="visible", timeout=15_000)
    options: list[ExperienceOption] = []
    checkboxes = dialog.locator('[role="checkbox"]')
    for index in range(await checkboxes.count()):
        checkbox = checkboxes.nth(index)
        label = re.sub(r"\s+", " ", (await checkbox.inner_text()).strip())
        aria_label = await checkbox.get_attribute("aria-label") or f"Filter by {label} experiences"
        if label:
            options.append(ExperienceOption(label, aria_label))
    return options


async def select_experiences(page: Page, options: Sequence[ExperienceOption]) -> None:
    dialog = page.get_by_role("dialog", name="Filter")
    if not options:
        await dialog.get_by_test_id("back-button").last.click()
        await page.get_by_test_id("select-date").wait_for(state="visible", timeout=20_000)
        return
    clear = dialog.get_by_role("button", name="Clear All", exact=True)
    if await clear.count() and await clear.is_enabled():
        await clear.click()
    for option in options:
        checkbox = dialog.locator('[role="checkbox"]').filter(has_text=re.compile(f"^{re.escape(option.label)}$", re.I))
        if not await checkbox.count():
            raise RuntimeError(f"Experience disappeared from the Filter dialog: {option.label}")
        if await checkbox.first.get_attribute("aria-checked") != "true":
            await checkbox.first.click()
    await dialog.get_by_role("button", name="Apply", exact=True).click()
    await page.get_by_test_id("select-date").wait_for(state="visible", timeout=20_000)


async def collect_date_options(page: Page) -> list[DateOption]:
    await page.get_by_test_id("select-date").click()
    dialog = page.get_by_role("dialog", name="Select date")
    await dialog.get_by_test_id("date-0").wait_for(state="visible", timeout=15_000)
    locators = dialog.locator('[data-testid^="date-"]')
    options: list[DateOption] = []
    for index in range(await locators.count()):
        locator = locators.nth(index)
        test_id = await locator.get_attribute("data-testid") or ""
        label = " — ".join(line.strip() for line in (await locator.inner_text()).splitlines() if line.strip())
        options.append(DateOption(test_id, label))
    if not options:
        raise RuntimeError("The Select date dialog opened, but no dates were found")
    return options


async def _back_from_drawer(page: Page, dialog_name: str) -> None:
    dialog = page.get_by_role("dialog", name=dialog_name)
    await dialog.get_by_test_id("back-button").last.click()
    await page.get_by_test_id("select-date").wait_for(state="visible", timeout=15_000)


async def select_date(page: Page, option: DateOption) -> None:
    current_dialog = page.get_by_role("dialog", name="Select date")
    if not await current_dialog.count() or not await current_dialog.is_visible():
        await page.get_by_test_id("select-date").click()
        current_dialog = page.get_by_role("dialog", name="Select date")
    await current_dialog.get_by_test_id(option.test_id).click()
    await page.get_by_test_id("select-date").wait_for(state="visible", timeout=20_000)
    await page.wait_for_timeout(700)


async def collect_preview_groups(page: Page) -> list[PreviewGroup]:
    groups = page.get_by_test_id("showtime-details-container")
    options: list[PreviewGroup] = []
    ignored_experiences = {"closed-captions", "descriptive-subtitles", "language-badge"}
    for index in range(await groups.count()):
        group = groups.nth(index)
        if not await group.get_by_test_id("seat-preview").count():
            continue
        experience_container = group.get_by_test_id("showtime-experiences-container")
        format_names: list[str] = []
        if await experience_container.count():
            markers = experience_container.locator("[data-testid]")
            for marker_index in range(await markers.count()):
                marker = markers.nth(marker_index)
                test_id = await marker.get_attribute("data-testid") or ""
                if test_id and test_id.casefold() not in ignored_experiences:
                    format_names.append(test_id)
        format_name = " + ".join(normalize_filter_options(format_names)) or "Regular"

        time_locators = group.locator('[data-testid^="showtime-cta-vistaId-"]')
        discovered_times: list[str] = []
        for time_index in range(await time_locators.count()):
            discovered_times.append(extract_time(await time_locators.nth(time_index).inner_text()))
        times = tuple(discovered_times)
        options.append(PreviewGroup(index=index, format_name=format_name, times=times))
    return options


async def _wait_for_seat_map(page: Page) -> None:
    await page.get_by_test_id("movie-title").wait_for(state="visible", timeout=30_000)
    await wait_for_preview_loader(page)
    seat = page.locator('[data-testid*="-seat-"]').first
    try:
        await seat.wait_for(state="attached", timeout=20_000)
    except PlaywrightTimeoutError:
        # Some sold-out or accessibility-only auditoriums can legitimately have
        # no standard seat marker. The page title still proves the preview loaded.
        pass
    await page.wait_for_timeout(150)
    await hide_preview_obstructions(page)


async def wait_for_preview_loader(
    page: Page,
    *,
    stable_hidden_ms: int = 750,
    timeout_ms: int = 30_000,
    poll_interval_ms: int = 100,
) -> None:
    """Wait until Cineplex's popcorn loading overlay stays gone.

    The previous seat SVG remains mounted while a new timeslot loads, so seat
    presence is not sufficient proof that the preview is ready.
    """
    loader = page.locator('[aria-label="loading..."], img[src*="popcorn-loader" i]')
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_ms / 1000
    hidden_since: float | None = None
    while loop.time() < deadline:
        is_visible = await loader.evaluate_all(
            """elements => elements.some(element => {
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                return rect.width > 0 && rect.height > 0 &&
                    style.display !== 'none' && style.visibility !== 'hidden' &&
                    Number(style.opacity || 1) > 0;
            })"""
        )
        now = loop.time()
        if is_visible:
            hidden_since = None
        elif hidden_since is None:
            hidden_since = now
        elif (now - hidden_since) * 1000 >= stable_hidden_ms:
            return
        await page.wait_for_timeout(poll_interval_ms)
    raise RuntimeError("Cineplex's popcorn seat-map loader did not disappear before the capture timeout")


async def hide_preview_obstructions(page: Page) -> bool:
    """Hide Cineplex's fixed action sheet before capturing the seat map.

    The preview page may recreate this footer when a different timeslot is
    selected, so callers intentionally run this after every seat-map load.
    """
    return await page.evaluate(
        """() => {
            const sheet = document.querySelector('[data-testid="bottom-sheet"]');
            if (!sheet) return false;
            const wrapper = sheet.closest('[class*="SimpleContainer_bottomSheet"]') || sheet;
            wrapper.setAttribute('data-crawler-hidden', 'bottom-sheet');
            wrapper.style.setProperty('display', 'none', 'important');
            return true;
        }"""
    )


async def collect_seat_metadata(page: Page) -> list[dict[str, object]]:
    raw_seats = await page.locator('[data-testid*="-seat-"]').evaluate_all(
        """elements => elements.map(element => {
            const rect = element.getBoundingClientRect();
            return {
                test_id: element.getAttribute('data-testid') || '',
                x: Math.round(rect.x * 10) / 10,
                y: Math.round(rect.y * 10) / 10,
                width: Math.round(rect.width * 10) / 10,
                height: Math.round(rect.height * 10) / 10
            };
        }).filter(seat => seat.width > 0 && seat.height > 0)"""
    )
    seats: list[dict[str, object]] = []
    for raw in raw_seats:
        parsed = parse_seat_test_id(str(raw.get("test_id", "")))
        if not parsed:
            continue
        parsed.update(
            {
                "x": float(raw["x"]),
                "y": float(raw["y"]),
                "width": float(raw["width"]),
                "height": float(raw["height"]),
            }
        )
        seats.append(parsed)
    seats.sort(key=lambda seat: (float(seat["y"]), float(seat["x"])))
    return seats


async def capture_preview_group(
    page: Page,
    group: PreviewGroup,
    movie: MovieOption,
    theatre: TheatreOption,
    date: DateOption,
    config: Config,
    max_screenshots: int | None,
    captured_so_far: int,
) -> list[dict[str, object]]:
    live_groups = page.get_by_test_id("showtime-details-container")
    if group.index >= await live_groups.count():
        raise RuntimeError(f"Showtime group {group.index + 1} disappeared before it could be opened")
    await live_groups.nth(group.index).get_by_test_id("seat-preview").click()
    await _wait_for_seat_map(page)

    timeslot_ids: list[str] = []
    time_buttons = page.locator('[data-testid^="showtime-"]')
    for index in range(await time_buttons.count()):
        test_id = await time_buttons.nth(index).get_attribute("data-testid") or ""
        if re.fullmatch(r"showtime-\d+", test_id):
            timeslot_ids.append(test_id)

    captures: list[dict[str, object]] = []
    for test_id in timeslot_ids:
        if max_screenshots is not None and captured_so_far + len(captures) >= max_screenshots:
            break
        button = page.get_by_test_id(test_id)
        button_text = re.sub(r"\s+", " ", (await button.inner_text()).strip())
        timeslot = extract_time(button_text)
        await button.click()
        await _wait_for_seat_map(page)
        seats = await collect_seat_metadata(page)
        output_path = unique_path(
            build_output_path(
                movie.title,
                theatre.name,
                group.format_name,
                date.label,
                timeslot,
                config.output_dir,
            )
        )
        await page.screenshot(path=str(output_path), full_page=True)
        captures.append(
            {
                "date": date.label,
                "date_iso": date_iso_from_label(date.label),
                "format": group.format_name,
                "timeslot": timeslot,
                "showtime_id": test_id.removeprefix("showtime-"),
                "path": str(output_path),
                "layout_signature": seat_layout_signature(seats),
                "rows": list(detected_ordinary_rows(seats)),
                "seats": seats,
            }
        )
        print(f"    Captured {group.format_name} at {timeslot}: {output_path.name}")

    await page.get_by_test_id("exit-button").click()
    await page.get_by_test_id("select-date").wait_for(state="visible", timeout=30_000)
    await page.wait_for_timeout(500)
    return captures


async def run_preview_loop(
    page: Page,
    movie: MovieOption,
    theatre: TheatreOption,
    dates: Sequence[DateOption],
    config: Config,
    max_screenshots: int | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    captures: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for date in dates:
        if max_screenshots is not None and len(captures) >= max_screenshots:
            break
        print(f"\nProcessing {date.label}")
        await select_date(page, date)
        groups = await collect_preview_groups(page)
        print(f"  Found {len(groups)} preview group(s).")
        for group in groups:
            if max_screenshots is not None and len(captures) >= max_screenshots:
                break
            try:
                captures.extend(
                    await capture_preview_group(
                        page,
                        group,
                        movie,
                        theatre,
                        date,
                        config,
                        max_screenshots,
                        len(captures),
                    )
                )
            except Exception as exc:
                errors.append(
                    {
                        "date": date.label,
                        "format": group.format_name,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                raise
    return captures, errors


def filter_captures_interactively(
    run_dir: Path, captures: list[dict[str, object]]
) -> dict[str, object]:
    timeslot_choices = build_timeslot_choices(captures)
    if not timeslot_choices:
        return {"status": "skipped", "reason": "No captured sessions were available"}

    selected_choices = prompt_multi_choice(
        timeslot_choices,
        "Select format/timeslot sessions to keep",
        lambda option: option.display_name,
    )
    selected_indexes = {
        index
        for choice in selected_choices
        for index in choice.capture_indexes
    }
    ticket_count = prompt_positive_int("How many side-by-side tickets do you need?")

    layout_groups = build_layout_groups(captures, selected_indexes)
    selected_rows_by_layout: dict[tuple[str, str], set[str]] = {}
    for group in layout_groups:
        selected_rows = prompt_row_selection(
            group.rows,
            f"Select acceptable rows for {group.display_name}",
        )
        selected_rows_by_layout[(group.format_name, group.signature)] = set(selected_rows)

    decisions: list[dict[str, object]] = []
    for index, capture in enumerate(captures):
        format_name = str(capture.get("format", "Unknown format"))
        signature = str(capture.get("layout_signature", ""))
        if index not in selected_indexes:
            keep = False
            reason = "format/timeslot session not selected"
            blocks: list[dict[str, object]] = []
        else:
            seats = capture.get("seats")
            selected_rows = selected_rows_by_layout.get((format_name, signature), set())
            if not isinstance(seats, list) or not seats:
                keep = False
                reason = "seat metadata unavailable"
                blocks = []
            elif not selected_rows:
                keep = False
                reason = "no acceptable rows selected for this layout"
                blocks = []
            else:
                blocks = find_adjacent_seat_blocks(seats, selected_rows, ticket_count)
                keep = bool(blocks)
                reason = (
                    f"at least {ticket_count} adjacent ordinary seats found"
                    if keep
                    else f"no block of {ticket_count} adjacent ordinary seats in selected rows"
                )
        decisions.append(
            {
                "capture_index": index,
                "keep": keep,
                "reason": reason,
                "qualifying_blocks": blocks,
            }
        )

    run_root = run_dir.resolve()
    filtered_dir = run_root / "filtered"
    discarded_dir = run_root / "discarded"
    filtered_dir.mkdir(parents=True, exist_ok=True)
    discarded_dir.mkdir(parents=True, exist_ok=True)

    kept_count = 0
    discarded_count = 0
    for decision in decisions:
        capture = captures[int(decision["capture_index"])]
        source = Path(str(capture.get("path", ""))).resolve()
        if not source.is_relative_to(run_root):
            raise RuntimeError(f"Refusing to move a screenshot outside the run directory: {source}")
        if not source.is_file():
            decision["move_status"] = "source missing"
            continue
        destination_dir = filtered_dir if decision["keep"] else discarded_dir
        destination = unique_path(destination_dir / source.name)
        shutil.move(str(source), str(destination))
        capture["original_path"] = str(source)
        capture["path"] = str(destination)
        capture["filter_status"] = "filtered" if decision["keep"] else "discarded"
        capture["filter_reason"] = decision["reason"]
        capture["qualifying_blocks"] = decision["qualifying_blocks"]
        decision["destination"] = str(destination)
        decision["move_status"] = "moved"
        if decision["keep"]:
            kept_count += 1
        else:
            discarded_count += 1

    row_selections = [
        {
            "format": group.format_name,
            "layout_signature": group.signature,
            "dates": list(group.date_labels),
            "detected_rows": list(group.rows),
            "selected_rows": [
                row
                for row in group.rows
                if row in selected_rows_by_layout.get((group.format_name, group.signature), set())
            ],
        }
        for group in layout_groups
    ]
    summary = {
        "status": "complete",
        "ticket_count": ticket_count,
        "selected_sessions": [choice.display_name for choice in selected_choices],
        "row_selections": row_selections,
        "kept": kept_count,
        "discarded": discarded_count,
        "filtered_dir": str(filtered_dir),
        "discarded_dir": str(discarded_dir),
        "decisions": decisions,
    }
    print(f"\nFiltering complete: {kept_count} kept, {discarded_count} discarded.")
    print(f"  Kept screenshots: {filtered_dir}")
    print(f"  Discarded screenshots: {discarded_dir}")
    return summary


def _split_cli_values(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []
    return normalize_filter_options(part for value in values for part in value.split(","))


def _serialize_config(config: Config) -> dict[str, object]:
    payload = asdict(config)
    payload["output_dir"] = str(config.output_dir)
    payload["documentation_dir"] = str(config.documentation_dir)
    return payload


def write_run_report(config: Config, report: dict[str, object]) -> Path:
    config.run_reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = unique_path(config.run_reports_dir / f"run-{timestamp}.json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture Cineplex seat-preview screenshots")
    parser.add_argument("--movie", help="Movie title (exact or unique partial match)")
    parser.add_argument("--theatre", help="Theatre name (exact or unique partial match)")
    parser.add_argument(
        "--experience",
        action="append",
        help="Experience name; repeat or comma-separate values. Use 'any' for no filtering.",
    )
    parser.add_argument(
        "--date",
        action="append",
        help="Date label; repeat or comma-separate values. Use 'all' for every visible date.",
    )
    parser.add_argument("--all-dates", action="store_true", help="Process every visible date")
    parser.add_argument("--max-distance-km", type=float, help="Override MAX_DISTANCE_KM")
    parser.add_argument("--max-screenshots", type=int, help="Stop after this many screenshots")
    parser.add_argument("--dry-run", action="store_true", help="Discover and select filters without opening seat previews")
    parser.add_argument(
        "--filter",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enter or skip post-crawl filtering without the initial yes/no prompt",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override the HEADLESS browser setting",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    config = load_config()
    if args.max_distance_km is not None:
        config = replace(config, max_distance_km=args.max_distance_km)
    if args.headless is not None:
        config = replace(config, headless=args.headless)
    if args.max_screenshots is not None and args.max_screenshots < 1:
        raise ValueError("--max-screenshots must be at least 1")

    started_at = datetime.now(timezone.utc)
    output_root = config.output_dir
    report: dict[str, object] = {
        "started_at": started_at.isoformat(),
        "status": "running",
        "output_root": str(output_root),
        "output_dir": None,
        "config": _serialize_config(config),
        "captures": [],
        "errors": [],
    }
    browser = None
    try:
        async with async_playwright() as playwright:
            launch_kwargs: dict[str, object] = {"headless": config.headless}
            if config.browser_channel:
                launch_kwargs["channel"] = config.browser_channel
            try:
                browser = await playwright.chromium.launch(**launch_kwargs)
            except Exception:
                if not config.browser_channel:
                    raise
                print(f"Could not launch {config.browser_channel}; falling back to Playwright Chromium.")
                browser = await playwright.chromium.launch(headless=config.headless)

            context_kwargs: dict[str, object] = {
                "viewport": {"width": 1440, "height": 1000},
                "locale": config.locale,
                "timezone_id": config.timezone_id,
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 Edg/131.0"
                ),
            }
            if config.geolocation:
                context_kwargs["geolocation"] = config.geolocation
                context_kwargs["permissions"] = ["geolocation"]
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            print("Opening Cineplex Tickets...")
            await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45_000)
            tickets_url = await open_tickets(page)
            report["tickets_url"] = tickets_url

            movies = await collect_movie_options(page)
            movie = (
                _match_named_choice(args.movie, movies, lambda option: option.title)
                if args.movie
                else (movies[0] if args.dry_run else prompt_single_choice(movies, "Select a movie", lambda option: option.title))
            )
            assert isinstance(movie, MovieOption)
            await select_movie(page, movie)
            report["movie"] = movie.title

            theatres = await collect_theatre_options(page, config.max_distance_km)
            theatre = (
                _match_named_choice(args.theatre, theatres, lambda option: option.name)
                if args.theatre
                else (
                    theatres[0]
                    if args.dry_run
                    else prompt_single_choice(theatres, "Select a theatre", lambda option: option.display_name)
                )
            )
            assert isinstance(theatre, TheatreOption)
            await select_theatre(page, theatre)
            report["theatre"] = asdict(theatre)

            run_output_dir = create_run_output_dir(
                output_root,
                started_at,
                movie.title,
                theatre.name,
            )
            config = replace(config, output_dir=run_output_dir)
            report["output_dir"] = str(run_output_dir)
            report["config"] = _serialize_config(config)
            print(f"Run output directory: {run_output_dir}")

            experiences = await collect_experience_options(page)
            cli_experiences = _split_cli_values(args.experience)
            if cli_experiences:
                if len(cli_experiences) == 1 and cli_experiences[0].casefold() in {"any", "none"}:
                    selected_experiences: list[ExperienceOption] = []
                elif len(cli_experiences) == 1 and cli_experiences[0].casefold() == "all":
                    selected_experiences = experiences
                else:
                    selected_experiences = [
                        _match_named_choice(value, experiences, lambda option: option.label)
                        for value in cli_experiences
                    ]
            elif args.dry_run:
                selected_experiences = []
            else:
                selected_experiences = prompt_multi_choice(
                    experiences,
                    "Select experiences",
                    lambda option: option.label,
                    blank_means_none=True,
                )
            await select_experiences(page, selected_experiences)
            report["experiences"] = [option.label for option in selected_experiences]

            dates = await collect_date_options(page)
            cli_dates = _split_cli_values(args.date)
            if args.all_dates or (len(cli_dates) == 1 and cli_dates[0].casefold() == "all"):
                selected_dates = dates
            elif cli_dates:
                selected_dates = [
                    _match_named_choice(value, dates, lambda option: option.label) for value in cli_dates
                ]
            elif args.dry_run:
                selected_dates = dates[:1]
            else:
                selected_dates = prompt_multi_choice(dates, "Select dates", lambda option: option.label)
            report["dates"] = [option.label for option in selected_dates]

            if args.dry_run:
                await _back_from_drawer(page, "Select date")
                report["status"] = "dry-run-complete"
                print(
                    f"Dry run complete: {movie.title} at {theatre.name}; "
                    f"{len(selected_dates)} date(s), {len(selected_experiences)} experience filter(s)."
                )
            else:
                # Date discovery leaves its drawer open; the loop selects the first date from it.
                captures, errors = await run_preview_loop(
                    page,
                    movie,
                    theatre,
                    selected_dates,
                    config,
                    args.max_screenshots,
                )
                report["captures"] = captures
                report["errors"] = errors
                report["status"] = "complete" if not errors else "complete-with-errors"
                print(f"\nCrawl complete: captured {len(captures)} screenshot(s) in {config.output_dir}")

                if captures:
                    should_filter = args.filter
                    if should_filter is None:
                        should_filter = prompt_yes_no("Continue with screenshot filtering?")
                    if should_filter:
                        report["filtering"] = filter_captures_interactively(config.output_dir, captures)
                    else:
                        report["filtering"] = {"status": "skipped", "reason": "User stopped after crawl"}

            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            await browser.close()
            browser = None
    except KeyboardInterrupt:
        report["status"] = "cancelled"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        print("\nCrawler cancelled by user.")
    except Exception as exc:
        report["status"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        errors = report.setdefault("errors", [])
        assert isinstance(errors, list)
        errors.append({"error": f"{type(exc).__name__}: {exc}"})
        print(f"\nCrawler failed: {type(exc).__name__}: {exc}")
    finally:
        if browser is not None:
            await browser.close()
        report_path = write_run_report(config, report)
        print(f"Run report: {report_path}")
    return 0 if report["status"] in {"complete", "dry-run-complete"} else 1


def main() -> int:
    return asyncio.run(run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
