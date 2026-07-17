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


def test_build_target_url_uses_live_movie_page():
    assert crawler.build_target_url("Inside Out 2") == "https://www.cineplex.com/en/movie/inside-out-2"


def test_resolve_selection_falls_back_to_defaults_when_empty():
    assert crawler.resolve_selection([], ["One", "Two", "Three"]) == ["One", "Two", "Three"]
