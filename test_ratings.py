"""Tests for player skill ratings, balanced generation and win probability."""

import itertools
import os

from logic import generate_teams, team_strength, win_probability
from players import PLAYERS
from ratings import (
    RATINGS_FILE,
    SKILLS,
    SKILLS_2,
    build_strengths,
    format_ratings_table,
    format_ratings_table_2,
    get_all_ratings,
    get_all_ratings2,
    is_complete as ratings_complete,
    is_complete_2,
    load_ratings,
    load_ratings2,
    performance_score,
    reset_ratings,
    reset_ratings2,
    set_player_skills,
    set_player_skills_2,
)

ALL_PLAYERS = [p for pair in PLAYERS.values() for p in pair]


def _complete_ratings(values_per_player: dict | None = None) -> dict:
    """Build a ratings dict with all 16 players rated."""
    ratings = {}
    for i, player in enumerate(ALL_PLAYERS):
        if values_per_player and player in values_per_player:
            v = values_per_player[player]
        else:
            # deterministic distinct values
            v = [(i + 1 + k) % 10 + 1 for k in range(len(SKILLS))]
        ratings[player] = {skill: v[j] for j, skill in enumerate(SKILLS)}
    return ratings


def _complete_ratings_2(values_per_player: dict | None = None) -> dict:
    """Build a 2-skill ratings dict with all 16 players rated."""
    ratings = {}
    for i, player in enumerate(ALL_PLAYERS):
        if values_per_player and player in values_per_player:
            v = values_per_player[player]
        else:
            v = [(i + 1 + k) % 10 + 1 for k in range(len(SKILLS_2))]
        ratings[player] = {skill: v[j] for j, skill in enumerate(SKILLS_2)}
    return ratings


def _strengths_from_5skill(ratings: dict) -> dict:
    """Convert full ratings dict to {player: total_strength}."""
    return {p: sum(ratings[p][s] for s in SKILLS) for p in ALL_PLAYERS}


# ---------------------------------------------------------------------------
# 5-skill tests
# ---------------------------------------------------------------------------

def test_set_and_get_rating(tmp_path):
    path = tmp_path / "ratings.json"
    set_player_skills("Sahand", {s: 8 for s in SKILLS}, str(path))
    assert get_all_ratings(str(path))["Sahand"] == {s: 8 for s in SKILLS}


def test_set_out_of_range(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="1 and 10"):
        set_player_skills(
            "Sahand",
            {"Dribbling": 11, "Passing": 5, "Finishing": 5, "Pace": 5, "Defending": 5},
            str(tmp_path / "ratings.json"),
        )


def test_set_rating_rejects_non_int(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="number"):
        set_player_skills(
            "Sahand",
            {"Dribbling": "x", "Passing": 5, "Finishing": 5, "Pace": 5, "Defending": 5},
            str(tmp_path / "ratings.json"),
        )


def test_reset_ratings(tmp_path):
    path = tmp_path / "ratings.json"
    set_player_skills("Sahand", {s: 7 for s in SKILLS}, str(path))
    reset_ratings(str(path))
    assert load_ratings(str(path)) == {}


def test_is_complete(tmp_path):
    path = tmp_path / "ratings.json"
    assert ratings_complete(load_ratings(str(path))) is False
    set_player_skills("Sahand", {s: 5 for s in SKILLS}, str(path))
    assert ratings_complete(load_ratings(str(path))) is False
    for player in ALL_PLAYERS:
        set_player_skills(player, {s: 5 for s in SKILLS}, str(path))
    assert ratings_complete(load_ratings(str(path))) is True


def test_format_ratings_table_contains_players(tmp_path):
    path = tmp_path / "ratings.json"
    for player in ALL_PLAYERS:
        set_player_skills(player, {s: 5 for s in SKILLS}, str(path))
    text = format_ratings_table(load_ratings(str(path)))
    for player in ALL_PLAYERS:
        assert player in text


def test_generate_teams_balanced_by_skill():
    ratings = _complete_ratings()
    strengths = _strengths_from_5skill(ratings)
    team_a, team_b = generate_teams(None, strengths)
    # Compute the minimal possible strength imbalance over all 2^8 assignments.
    positions = list(PLAYERS.keys())
    pairs = [PLAYERS[pos] for pos in positions]
    best = min(
        abs(sum(strengths[pairs[i][bits[i]]] for i in range(len(positions)))
            - sum(strengths[pairs[i][1 - bits[i]]] for i in range(len(positions))))
        for bits in itertools.product([0, 1], repeat=len(positions))
    )
    chosen = abs(team_strength(team_a, strengths) - team_strength(team_b, strengths))
    assert chosen == best


def test_generate_teams_respects_position_constraint_with_ratings():
    ratings = _complete_ratings()
    strengths = _strengths_from_5skill(ratings)
    for _ in range(50):
        team_a, team_b = generate_teams(None, strengths)
        assert set(team_a.keys()) == set(PLAYERS.keys())
        for position, pair in PLAYERS.items():
            assert team_a[position] in pair
            assert team_b[position] in pair
            assert team_a[position] != team_b[position]


def test_generate_teams_without_ratings_uses_history():
    team_a, team_b = generate_teams({"Mohammd Hosein": 5, "Hani": 0})
    assert team_a["GK"] == "Hani"


def test_win_probability_sums_to_100():
    ratings = _complete_ratings()
    strengths = _strengths_from_5skill(ratings)
    team_a, team_b = generate_teams(None, strengths)
    p_a, p_b = win_probability(team_a, team_b, strengths)
    assert p_a + p_b == 100


def test_win_probability_equal_strength():
    ratings = _complete_ratings({p: [10, 10, 10, 10, 10] for p in ALL_PLAYERS})
    strengths = _strengths_from_5skill(ratings)
    team_a = {pos: PLAYERS[pos][0] for pos in PLAYERS}
    team_b = {pos: PLAYERS[pos][1] for pos in PLAYERS}
    assert win_probability(team_a, team_b, strengths) == (50, 50)


# ---------------------------------------------------------------------------
# 2-skill tests
# ---------------------------------------------------------------------------

def test_set_and_get_rating_2(tmp_path):
    path = tmp_path / "ratings2.json"
    set_player_skills_2("Sahand", {"Attacking": 8, "Defending": 5}, str(path))
    assert get_all_ratings2(str(path))["Sahand"] == {"Attacking": 8, "Defending": 5}


def test_set_out_of_range_2(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="1 and 10"):
        set_player_skills_2("Sahand", {"Attacking": 11, "Defending": 5}, str(tmp_path / "ratings2.json"))


def test_is_complete_2(tmp_path):
    path = tmp_path / "ratings2.json"
    assert is_complete_2(load_ratings2(str(path))) is False
    for player in ALL_PLAYERS:
        set_player_skills_2(player, {"Attacking": 5, "Defending": 5}, str(path))
    assert is_complete_2(load_ratings2(str(path))) is True


def test_reset_ratings_2(tmp_path):
    path = tmp_path / "ratings2.json"
    set_player_skills_2("Sahand", {"Attacking": 7, "Defending": 5}, str(path))
    reset_ratings2(str(path))
    assert load_ratings2(str(path)) == {}


def test_generate_teams_balanced_by_2skill():
    ratings = _complete_ratings_2()
    strengths = {p: sum(ratings[p][s] for s in SKILLS_2) for p in ALL_PLAYERS}
    team_a, team_b = generate_teams(None, strengths)
    positions = list(PLAYERS.keys())
    pairs = [PLAYERS[pos] for pos in positions]
    best = min(
        abs(sum(strengths[pairs[i][bits[i]]] for i in range(len(positions)))
            - sum(strengths[pairs[i][1 - bits[i]]] for i in range(len(positions))))
        for bits in itertools.product([0, 1], repeat=len(positions))
    )
    chosen = abs(team_strength(team_a, strengths) - team_strength(team_b, strengths))
    assert chosen == best


def test_format_ratings_table_2(tmp_path):
    path = tmp_path / "ratings2.json"
    for player in ALL_PLAYERS:
        set_player_skills_2(player, {"Attacking": 5, "Defending": 5}, str(path))
    text = format_ratings_table_2(load_ratings2(str(path)))
    for player in ALL_PLAYERS:
        assert player in text


# ---------------------------------------------------------------------------
# Performance rating tests
# ---------------------------------------------------------------------------

def test_performance_score_zero():
    assert performance_score("Sahand") == 0


def test_performance_score_goals_and_assists():
    stats = {
        "weeks": {
            "1": {
                "goals": {"Sahand": 2, "Hani": 0},
                "assists": {"Sahand": 1, "Hani": 3},
            }
        }
    }
    assert performance_score("Sahand", stats) == 2 * 3 + 1 * 2  # 8
    assert performance_score("Hani", stats) == 0 * 3 + 3 * 2   # 6


def test_performance_team_strength():
    stats = {
        "weeks": {
            "1": {
                "goals": {"Sahand": 2},
                "assists": {"Sahand": 1},
            }
        }
    }
    strengths = {p: performance_score(p, stats) for p in ALL_PLAYERS}
    assert strengths["Sahand"] == 8
    # All other players are 0
    assert sum(v for k, v in strengths.items() if k != "Sahand") == 0


# ---------------------------------------------------------------------------
# build_strengths tests
# ---------------------------------------------------------------------------

def test_build_strengths_5skill():
    ratings = _complete_ratings()
    strengths = build_strengths("5skill", ratings_5=ratings)
    assert strengths is not None
    assert len(strengths) == 16


def test_build_strengths_2skill():
    ratings = _complete_ratings_2()
    strengths = build_strengths("2skill", ratings_2=ratings)
    assert strengths is not None
    assert len(strengths) == 16


def test_build_strengths_performance():
    stats = {
        "weeks": {
            "1": {
                "goals": {"Sahand": 2},
                "assists": {"Sahand": 1},
            }
        }
    }
    strengths = build_strengths("performance", stats=stats)
    assert strengths is not None
    assert strengths["Sahand"] == 8


def test_build_strengths_returns_none_when_incomplete():
    assert build_strengths("5skill", ratings_5={}) is None
    assert build_strengths("2skill", ratings_2={}) is None
    # Performance with all zeros returns None (no data)
    assert build_strengths("performance", stats={}) is None
