import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import crawler  # noqa: E402


def test_normalize_filter_options_removes_duplicates_and_blank_entries():
    values = [" Regular ", "3D", "regular", "UltraAVX", "   ", "", None]

    assert crawler.normalize_filter_options(values) == ["Regular", "3D", "UltraAVX"]


def test_parse_distance_extracts_compact_and_decimal_km_values():
    assert crawler.parse_distance("1km") == 1
    assert crawler.parse_distance("12.5 km away") == 12.5
    assert crawler.parse_distance("No distance") is None


def test_clean_movie_label_only_removes_advance_ticket_suffix():
    assert crawler.clean_movie_label("The Odyssey\nAdvance ticket") == "The Odyssey"
    assert crawler.clean_movie_label("Toy Story 5 Special Experience") == "Toy Story 5 Special Experience"


def test_extract_time_ignores_relative_date_text():
    assert crawler.extract_time("2:45 PM\nTomorrow") == "2:45 PM"


def test_safe_filename_is_stable_and_bounded():
    assert crawler.safe_filename("A/B & C") == "A_B_C"
    assert len(crawler.safe_filename("x" * 100, max_length=20)) == 20


def test_build_output_path_contains_all_workflow_dimensions(tmp_path):
    path = crawler.build_output_path(
        "Movie / One",
        "Cinema & Two",
        "IMAX 3D",
        "Friday, July 17",
        "7:30 PM",
        tmp_path,
    )

    assert path.parent == tmp_path
    assert path.name == "Movie_One-Cinema_Two-IMAX_3D-Friday_July_17-7_30_PM.png"


def test_unique_path_adds_suffix_without_overwriting(tmp_path):
    original = tmp_path / "capture.png"
    original.touch()

    assert crawler.unique_path(original) == tmp_path / "capture_2.png"


def test_create_run_output_dir_uses_timestamp_and_avoids_collisions(tmp_path):
    started_at = datetime(2026, 7, 17, 3, 15, 30, tzinfo=timezone.utc)

    first = crawler.create_run_output_dir(
        tmp_path / "output",
        started_at,
        "The Odyssey",
        "Cineplex Yonge-Eglinton",
    )
    second = crawler.create_run_output_dir(
        tmp_path / "output",
        started_at,
        "The Odyssey",
        "Cineplex Yonge-Eglinton",
    )

    expected = "20260717-031530-The_Odyssey-Cineplex_Yonge-Eglinton"
    assert first == tmp_path / "output" / expected
    assert second == tmp_path / "output" / f"{expected}_2"
    assert first.is_dir()
    assert second.is_dir()


def test_load_config_resolves_paths_from_repository_and_environment_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "screens"))
    monkeypatch.setenv("MAX_DISTANCE_KM", "12.5")
    monkeypatch.setenv("HEADLESS", "true")
    monkeypatch.setenv("LATITUDE", "43.65")
    monkeypatch.setenv("LONGITUDE", "-79.38")

    config = crawler.load_config()

    assert config.output_dir == (tmp_path / "screens").resolve()
    assert config.max_distance_km == 12.5
    assert config.headless is True
    assert config.geolocation == {"latitude": 43.65, "longitude": -79.38, "accuracy": 100.0}


def test_load_config_rejects_half_configured_geolocation(monkeypatch):
    monkeypatch.setenv("LATITUDE", "43.65")
    monkeypatch.setenv("LONGITUDE", "")

    with pytest.raises(ValueError, match="must either both be set"):
        crawler.load_config()


def test_named_choice_requires_a_unique_match():
    options = ["Cineplex Toronto", "Cineplex Toronto VIP", "Cineplex Vaughan"]

    assert crawler._match_named_choice("Vaughan", options, str) == "Cineplex Vaughan"
    with pytest.raises(ValueError, match="ambiguous"):
        crawler._match_named_choice("Toronto", options, str)


class _FakeQuestion:
    def __init__(self, answer):
        self.answer = answer

    def ask(self):
        return self.answer


class _FakeChoice:
    def __init__(self, title, value=None, **_kwargs):
        self.title = title
        self.value = title if value is None else value


class _FakeQuestionary:
    Choice = _FakeChoice

    def __init__(self, answers):
        self.answers = iter(answers)
        self.calls = []

    def select(self, message, **kwargs):
        self.calls.append(("select", message, kwargs))
        return _FakeQuestion(next(self.answers))

    def checkbox(self, message, **kwargs):
        self.calls.append(("checkbox", message, kwargs))
        return _FakeQuestion(next(self.answers))


def test_key_driven_menus_cover_all_interactive_prompt_types(monkeypatch):
    movies = ["Movie A", "Movie B"]
    fake = _FakeQuestionary(
        [
            movies[1],
            movies,
            ["B", "C"],
            "Yes",
            4,
        ]
    )
    monkeypatch.setattr(crawler, "questionary", fake)
    monkeypatch.setattr(crawler, "_console_menu_available", lambda: True)

    assert crawler.prompt_single_choice(movies, "Select a movie") == "Movie B"
    assert crawler.prompt_multi_choice(movies, "Select movies") == movies
    assert crawler.prompt_row_selection(["A", "B", "C"], "Select rows") == ["B", "C"]
    assert crawler.prompt_yes_no("Continue?") is True
    assert crawler.prompt_positive_int("How many tickets?") == 4

    assert [call[0] for call in fake.calls] == [
        "select",
        "checkbox",
        "checkbox",
        "select",
        "select",
    ]
    checkbox_instructions = [call[2]["instruction"] for call in fake.calls if call[0] == "checkbox"]
    assert all("Space to toggle" in instruction for instruction in checkbox_instructions)


def test_key_driven_menu_cancellation_raises_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(crawler, "questionary", _FakeQuestionary([None]))
    monkeypatch.setattr(crawler, "_console_menu_available", lambda: True)

    with pytest.raises(KeyboardInterrupt):
        crawler.prompt_single_choice(["Movie A"], "Select a movie")


def test_real_questionary_widgets_accept_prompt_configuration(monkeypatch):
    if crawler.questionary is None:
        pytest.skip("questionary is not installed")
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    monkeypatch.setattr(crawler, "_console_menu_available", lambda: True)

    with create_pipe_input() as pipe_input, create_app_session(
        input=pipe_input,
        output=DummyOutput(),
    ):
        monkeypatch.setattr(crawler, "_ask_console_question", lambda _question: "Movie A")
        assert crawler.prompt_single_choice(["Movie A"], "Select a movie") == "Movie A"

        multi_answers = iter([["IMAX"], ["A"]])
        monkeypatch.setattr(crawler, "_ask_console_question", lambda _question: next(multi_answers))
        assert crawler.prompt_multi_choice(["IMAX"], "Select formats") == ["IMAX"]
        assert crawler.prompt_row_selection(["A"], "Select rows") == ["A"]

        monkeypatch.setattr(crawler, "_ask_console_question", lambda _question: "No")
        assert crawler.prompt_yes_no("Continue?") is False

        monkeypatch.setattr(crawler, "_ask_console_question", lambda _question: 2)
        assert crawler.prompt_positive_int("How many tickets?") == 2


def test_build_target_url_uses_live_movie_page():
    assert crawler.build_target_url("Inside Out 2") == "https://www.cineplex.com/en/movie/inside-out-2"


def test_resolve_selection_falls_back_to_defaults_when_empty():
    assert crawler.resolve_selection([], ["One", "Two", "Three"]) == ["One", "Two", "Three"]


def _seat(test_id, x, y=100):
    seat = crawler.parse_seat_test_id(test_id)
    assert seat is not None
    seat.update({"x": x, "y": y, "width": 20.0, "height": 20.0})
    return seat


def test_parse_seat_test_id_distinguishes_ordinary_and_special_seats():
    standard = _seat("Standard-available-seat-A12", 0)
    sofa = _seat("SofaLeft-available-seat-A11", 20)
    dbox = _seat("Dbox-available-seat-A10", 40)
    companion = _seat("Companion-available-seat-AC9", 60)

    assert standard["row"] == "A"
    assert standard["number"] == 12
    assert crawler.is_ordinary_seat(standard)
    assert crawler.is_ordinary_seat(sofa)
    assert not crawler.is_ordinary_seat(dbox)
    assert not crawler.is_ordinary_seat(companion)


def test_adjacent_blocks_exclude_occupied_special_and_across_aisle_seats():
    seats = [
        _seat("Standard-available-seat-A1", 0),
        _seat("Standard-available-seat-A2", 20),
        _seat("Standard-occupied-seat-A3", 40),
        _seat("Standard-available-seat-A4", 60),
        _seat("Standard-available-seat-A5", 80),
        # Consecutive numbers, but the rendered gap represents an aisle.
        _seat("Standard-available-seat-A6", 140),
        _seat("Standard-available-seat-A7", 160),
        _seat("Dbox-available-seat-A8", 180),
    ]

    blocks = crawler.find_adjacent_seat_blocks(seats, {"A"}, 2)

    assert [block["seats"] for block in blocks] == [["A1", "A2"], ["A4", "A5"], ["A6", "A7"]]
    assert crawler.find_adjacent_seat_blocks(seats, {"A"}, 3) == []


def test_timeslot_choices_split_when_schedule_changes():
    captures = [
        {"format": "IMAX", "date": "Friday — July 17, 2026", "timeslot": "11:00 AM"},
        {"format": "IMAX", "date": "Friday — July 17, 2026", "timeslot": "3:00 PM"},
        {"format": "IMAX", "date": "Saturday — July 18, 2026", "timeslot": "11:00 AM"},
        {"format": "IMAX", "date": "Saturday — July 18, 2026", "timeslot": "3:00 PM"},
        {"format": "IMAX", "date": "Sunday — July 19, 2026", "timeslot": "12:00 PM"},
        {"format": "IMAX", "date": "Sunday — July 19, 2026", "timeslot": "4:00 PM"},
    ]

    choices = crawler.build_timeslot_choices(captures)

    assert [choice.timeslot for choice in choices] == ["11:00 AM", "3:00 PM", "12:00 PM", "4:00 PM"]
    assert choices[0].period_labels == ("Friday — July 17, 2026", "Saturday — July 18, 2026")
    assert choices[2].period_labels == ("Sunday — July 19, 2026",)


def test_row_selection_accepts_letters_commas_and_ranges():
    rows = ["AA", "BB", "CC", "DD", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

    assert crawler.parse_row_selection("A,B,C,F-J", rows) == ["A", "B", "C", "F", "G", "H", "I", "J"]
    assert crawler.parse_row_selection("aa-dd", rows) == ["AA", "BB", "CC", "DD"]
    assert crawler.parse_row_selection("A", rows) == ["A"]
    assert crawler.parse_row_selection("all", rows) == rows


def test_row_selection_rejects_unknown_and_reverse_ranges():
    with pytest.raises(ValueError, match="Unknown row"):
        crawler.parse_row_selection("Z", ["A", "B", "C"])
    with pytest.raises(ValueError, match="displayed order"):
        crawler.parse_row_selection("C-A", ["A", "B", "C"])


def test_interactive_filter_moves_matches_and_leftovers(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    first_path = run_dir / "first.png"
    second_path = run_dir / "second.png"
    first_path.write_bytes(b"first")
    second_path.write_bytes(b"second")
    available_layout = [
        _seat("Standard-available-seat-A1", 0),
        _seat("Standard-available-seat-A2", 20),
    ]
    unavailable_layout = [
        _seat("Standard-available-seat-A1", 0),
        _seat("Standard-occupied-seat-A2", 20),
    ]
    signature = crawler.seat_layout_signature(available_layout)
    assert signature == crawler.seat_layout_signature(unavailable_layout)
    captures = [
        {
            "format": "IMAX",
            "date": "Friday — July 17, 2026",
            "timeslot": "2:00 PM",
            "path": str(first_path),
            "layout_signature": signature,
            "seats": available_layout,
        },
        {
            "format": "IMAX",
            "date": "Friday — July 17, 2026",
            "timeslot": "6:00 PM",
            "path": str(second_path),
            "layout_signature": signature,
            "seats": unavailable_layout,
        },
    ]
    answers = iter(["a", "2", "all"])
    monkeypatch.setattr(crawler, "_console_menu_available", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    summary = crawler.filter_captures_interactively(run_dir, captures)

    assert summary["kept"] == 1
    assert summary["discarded"] == 1
    assert (run_dir / "filtered" / "first.png").is_file()
    assert (run_dir / "discarded" / "second.png").is_file()
    assert captures[0]["filter_status"] == "filtered"
    assert captures[1]["filter_status"] == "discarded"


class _FakeLoaderLocator:
    def __init__(self, visibility):
        self.visibility = iter(visibility)
        self.last = False
        self.calls = 0

    async def evaluate_all(self, _script):
        self.calls += 1
        self.last = next(self.visibility, self.last)
        return self.last


class _FakeLoaderPage:
    def __init__(self, visibility):
        self.loader = _FakeLoaderLocator(visibility)

    def locator(self, selector):
        assert "popcorn-loader" in selector
        return self.loader

    async def wait_for_timeout(self, milliseconds):
        await asyncio.sleep(milliseconds / 1000)


def test_preview_loader_must_remain_hidden_before_capture():
    page = _FakeLoaderPage([True, True, False, False, False])

    asyncio.run(
        crawler.wait_for_preview_loader(
            page,
            stable_hidden_ms=2,
            timeout_ms=100,
            poll_interval_ms=1,
        )
    )

    assert page.loader.calls >= 4


def test_preview_loader_timeout_fails_instead_of_capturing():
    page = _FakeLoaderPage([True])

    with pytest.raises(RuntimeError, match="popcorn seat-map loader"):
        asyncio.run(
            crawler.wait_for_preview_loader(
                page,
                stable_hidden_ms=2,
                timeout_ms=5,
                poll_interval_ms=1,
            )
        )
