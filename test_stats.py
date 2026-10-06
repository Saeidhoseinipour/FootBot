"""Tests for the stats storage/aggregation/parsing logic (no Telegram needed)."""

import pytest

from players import PLAYERS
from stats import (
    aggregate_stats,
    format_overall_stats,
    format_week_stats,
    get_week_record,
    load_stats,
    parse_record_input,
    set_week_record,
)

ALL_PLAYER_NAMES = {player for pair in PLAYERS.values() for player in pair}


def test_set_week_record_and_reload(tmp_path):
    path = tmp_path / "stats.json"
    set_week_record(1, [("Sahand", 2, 1), ("Hani", 1, 2)], str(path))
    data = get_week_record(1, str(path))
    assert data == {"goals": {"Sahand": 2, "Hani": 1}, "assists": {"Sahand": 1, "Hani": 2}}


def test_same_week_overwrites_previous_record(tmp_path):
    path = tmp_path / "stats.json"
    set_week_record(2, [("Sahand", 3, 0)], str(path))
    set_week_record(2, [("Sahand", 5, 4)], str(path))
    data = get_week_record(2, str(path))
    assert data["goals"]["Sahand"] == 5
    assert data["assists"]["Sahand"] == 4


def test_aggregate_sums_across_weeks(tmp_path):
    path = tmp_path / "stats.json"
    set_week_record(1, [("Sahand", 2, 1), ("Hani", 1, 0)], str(path))
    set_week_record(2, [("Sahand", 3, 2), ("Milad", 0, 3)], str(path))
    stored = get_week_record(1, str(path)) and load_stats(str(path))
    totals = aggregate_stats(stored)
    assert totals["Sahand"] == {"goals": 5, "assists": 3}
    assert totals["Hani"] == {"goals": 1, "assists": 0}
    assert totals["Milad"] == {"goals": 0, "assists": 3}


def test_parse_record_input_valid():
    week, records = parse_record_input(
        "/record 3 Sahand:2:1, Hani:1:2 , Saeed:0:1", ALL_PLAYER_NAMES
    )
    assert week == 3
    assert records == [("Sahand", 2, 1), ("Hani", 1, 2), ("Saeed", 0, 1)]


@pytest.mark.parametrize(
    "text, message",
    [
        ("/record", "No week given"),
        ("/record abc Sahand:1:0", "week must be a number"),
        ("/record 0 Sahand:1:0", "positive"),
        ("/record 3", "No entries given"),
        ("/record 3 Sahand:1", "Bad entry"),
        ("/record 3 UnknownPlayer:1:0", "Unknown player"),
        ("/record 3 Sahand:x:0", "must be numbers"),
        ("/record 3 Sahand:-1:0", "cannot be negative"),
    ],
)
def test_parse_record_input_rejects_bad_input(text, message):
    with pytest.raises(ValueError, match=message):
        parse_record_input(text, ALL_PLAYER_NAMES)


def test_format_overall_stats_empty():
    assert "No goals or assists" in format_overall_stats({})


def test_format_overall_stats_ranks_by_goals():
    text = format_overall_stats({"Sahand": {"goals": 2, "assists": 1}, "Hani": {"goals": 5, "assists": 0}})
    assert text.index("Hani") < text.index("Sahand")


def test_format_week_stats_shows_data():
    text = format_week_stats({"goals": {"Hani": 1}, "assists": {}}, 3)
    assert "Week 3" in text
    assert "Hani — 1" in text
    assert "No assists recorded" in text