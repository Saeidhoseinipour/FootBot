"""Tests for the balanced (fairness) team generation and draw history."""

import os

from draw_history import load_history, record_draw, save_history, team_a_counts
from logic import generate_teams
from players import PLAYERS

ALL_PLAYER_NAMES = {player for pair in PLAYERS.values() for player in pair}


def test_generate_teams_balanced_gives_team_a_to_less_common_player():
    counts = {"Mohammd Hosein": 5, "Hani": 0}
    for _ in range(20):
        team_a, team_b = generate_teams(counts)
        assert team_a["GK"] == "Hani"
        assert team_b["GK"] == "Mohammd Hosein"


def test_generate_teams_balanced_keeps_one_per_position():
    counts = {"Mohammd Hosein": 3, "Hani": 1}
    for _ in range(20):
        team_a, team_b = generate_teams(counts)
        assert set(team_a.keys()) == set(PLAYERS.keys())
        assert set(team_b.keys()) == set(PLAYERS.keys())
        for position, pair in PLAYERS.items():
            assert team_a[position] in pair
            assert team_b[position] in pair
            assert team_a[position] != team_b[position]


def test_generate_teams_balanced_ties_still_random():
    # Equal counts must still produce both assignments eventually.
    counts = {"Sahand": 1, "Ali": 1}
    outcomes = set()
    for _ in range(100):
        team_a, _ = generate_teams(counts)
        outcomes.add(team_a["FW"])
    assert outcomes == {"Sahand", "Ali"}


def test_record_draw_increments_team_a_counts(tmp_path):
    path = tmp_path / "history.json"
    team_a = {"FW": "Sahand", "GK": "Hani"}
    team_b = {"FW": "Ali", "GK": "Mohammd Hosein"}
    record_draw(team_a, team_b, str(path))

    counts = team_a_counts(str(path))
    assert counts == {"Sahand": 1, "Hani": 1}
    history = load_history(str(path))
    assert len(history["draws"]) == 1


def test_record_draw_multiple_draws(tmp_path):
    path = tmp_path / "history.json"
    record_draw({"FW": "Sahand"}, {"FW": "Ali"}, str(path))
    record_draw({"FW": "Ali"}, {"FW": "Sahand"}, str(path))
    counts = team_a_counts(str(path))
    assert counts["Sahand"] == 1
    assert counts["Ali"] == 1


def test_load_history_missing_file(tmp_path):
    assert load_history(str(tmp_path / "none.json")) == {"counts": {}, "draws": []}


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "history.json"
    save_history({"counts": {"Sahand": 2}, "draws": []}, str(path))
    assert os.path.exists(path)
    assert load_history(str(path)) == {"counts": {"Sahand": 2}, "draws": []}