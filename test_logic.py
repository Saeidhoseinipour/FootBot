"""Tests for the pure team-generation logic."""

from players import PLAYERS
from logic import generate_teams


def test_each_team_has_exactly_8_players():
    team_a, team_b = generate_teams()
    assert len(team_a) == 8
    assert len(team_b) == 8


def test_each_team_has_exactly_one_player_per_position():
    team_a, team_b = generate_teams()
    assert set(team_a.keys()) == set(PLAYERS.keys())
    assert set(team_b.keys()) == set(PLAYERS.keys())


def test_two_players_of_a_position_never_on_same_team():
    for _ in range(200):
        team_a, team_b = generate_teams()
        for position, pair in PLAYERS.items():
            # Both players must be used, one per team.
            assert team_a[position] in pair
            assert team_b[position] in pair
            assert team_a[position] != team_b[position]


def test_all_16_players_are_used_exactly_once_per_draw():
    for _ in range(200):
        team_a, team_b = generate_teams()
        all_players = list(team_a.values()) + list(team_b.values())
        assert len(all_players) == len(set(all_players)) == 16
        # Every draw consumes the whole pool.
        assert set(all_players) == {p for pair in PLAYERS.values() for p in pair}