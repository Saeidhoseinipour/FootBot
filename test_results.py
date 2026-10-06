"""Tests for match results, win/loss records and the ranked player table."""

from players import PLAYERS
from stats import (
    format_player_table,
    get_result,
    load_stats,
    player_records,
    set_result,
)

TEAM_A = {"GK": "Hani", "CB": "Amin", "FW": "Sahand"}
TEAM_B = {"GK": "Mohammd Hosein", "CB": "Saeed", "FW": "Ali"}


def _records(stats: dict) -> dict:
    return {"results": stats["results"]}


def test_set_and_get_result(tmp_path):
    path = tmp_path / "stats.json"
    set_result(1, 4, 2, TEAM_A, TEAM_B, str(path))
    result = get_result(1, str(path))
    assert result["score_a"] == 4
    assert result["score_b"] == 2
    assert result["team_a"] == TEAM_A


def test_player_records_win_loss(tmp_path):
    path = tmp_path / "stats.json"
    set_result(1, 4, 2, TEAM_A, TEAM_B, str(path))
    records = player_records(_records(load_stats(str(path))))
    for player in TEAM_A.values():
        assert records[player]["wins"] == 1
        assert records[player]["games"] == 1
    for player in TEAM_B.values():
        assert records[player]["losses"] == 1
        assert records[player]["games"] == 1


def test_player_records_draw(tmp_path):
    path = tmp_path / "stats.json"
    set_result(1, 2, 2, TEAM_A, TEAM_B, str(path))
    records = player_records(_records(load_stats(str(path))))
    for player in list(TEAM_A.values()) + list(TEAM_B.values()):
        assert records[player]["draws"] == 1
        assert records[player]["wins"] == 0
        assert records[player]["losses"] == 0


def test_player_records_accumulate_across_weeks(tmp_path):
    path = tmp_path / "stats.json"
    set_result(1, 1, 0, TEAM_A, TEAM_B, str(path))
    set_result(2, 0, 1, TEAM_A, TEAM_B, str(path))
    records = player_records(_records(load_stats(str(path))))
    for player in TEAM_A.values():
        assert records[player] == {"wins": 1, "losses": 1, "draws": 0, "games": 2}


def test_player_table_ranks_by_win_percentage():
    stats = {
        "results": {
            "1": {"score_a": 5, "score_b": 0, "team_a": TEAM_A, "team_b": TEAM_B},
        }
    }
    text = format_player_table(_records(stats))
    # Team A players (100%) must appear before Team B players (0%).
    assert text.index("Sahand") < text.index("Ali")
    assert text.index("Hani") < text.index("Mohammd Hosein")


def test_player_table_includes_all_16_players():
    stats = {"results": {}, "weeks": {}}
    text = format_player_table(stats)
    for player in {p for pair in PLAYERS.values() for p in pair}:
        assert player in text


def test_player_table_shows_goals_and_assists():
    stats = {
        "weeks": {"1": {"goals": {"Sahand": 3}, "assists": {"Sahand": 2}}},
        "results": {},
    }
    text = format_player_table(stats)
    assert "Sahand" in text


def test_format_player_table_empty_has_header():
    text = format_player_table({"results": {}, "weeks": {}})
    assert "Rank" in text
    assert "Player" in text
    assert "W%" in text