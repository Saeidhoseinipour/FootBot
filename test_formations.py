"""Tests for formation config, settings persistence and pitch rendering."""

import os

import pytest

from formations import (
    DEFAULT_FORMATION,
    FORMATIONS,
    add_formation,
    all_formations,
    format_formation_team,
    get_custom_formations,
    get_formation,
    render_pitch,
    set_formation,
)
from players import PLAYERS

ALL_POSITIONS = set(PLAYERS.keys())


def test_every_formation_uses_all_positions_once():
    for name, lines in FORMATIONS.items():
        used = [pos for positions in lines.values() for pos in positions]
        assert set(used) == ALL_POSITIONS
        assert len(used) == len(ALL_POSITIONS)


def test_default_formation_defined():
    assert DEFAULT_FORMATION in FORMATIONS


def test_get_formation_defaults_when_no_settings(tmp_path):
    assert get_formation(str(tmp_path / "settings.json")) == DEFAULT_FORMATION


def test_set_and_get_formation_roundtrip(tmp_path):
    settings_file = tmp_path / "settings.json"
    set_formation("3-2-2", str(settings_file))
    assert get_formation(str(settings_file)) == "3-2-2"


def test_set_formation_rejects_unknown(tmp_path):
    with pytest.raises(ValueError, match="Unknown formation"):
        set_formation("9-9-9", str(tmp_path / "settings.json"))


def test_render_pitch_contains_positions_and_players():
    team = {pos: f"P_{pos}" for pos in ALL_POSITIONS}
    pitch = render_pitch(team, "3-3-1")
    assert "GK:" in pitch
    assert "FW:" in pitch
    assert "RB:" in pitch
    assert "┌" in pitch and "└" in pitch
    for pos in ALL_POSITIONS:
        assert f"{pos}: P_{pos}" in pitch


def test_format_formation_team_has_label_and_diagram():
    team = {pos: "X" for pos in ALL_POSITIONS}
    text = format_formation_team(team, "3-3-1", "Team A")
    assert "Team A" in text
    assert "3-3-1" in text
    assert "┌" in text


def test_formation_validation_rejects_bad_formation(monkeypatch):
    import formations

    bad = dict(formations.FORMATIONS)
    bad["bad"] = {"Attack": ["FW", "FW"], "Goalkeeper": ["GK"]}
    monkeypatch.setattr(formations, "FORMATIONS", bad)
    with pytest.raises(ValueError):
        formations._validate_formations()


def test_add_custom_formation_and_list(tmp_path):
    settings_file = tmp_path / "settings.json"
    add_formation("2-3-2x", ["CB", "RB"], ["CM", "RM", "LB"], ["FW", "LM"], str(settings_file))
    customs = get_custom_formations(str(settings_file))
    assert "2-3-2x" in customs
    assert customs["2-3-2x"]["Defense"] == ["CB", "RB"]
    assert set(customs["2-3-2x"]["Midfield"]) == {"CM", "RM", "LB"}
    assert "2-3-2x" in all_formations(str(settings_file))


def test_add_custom_rejects_missing_position(tmp_path):
    settings_file = tmp_path / "settings.json"
    with pytest.raises(ValueError, match="all 8 positions"):
        add_formation("1-1-1", ["CB"], ["CM"], ["FW"], str(settings_file))


def test_add_custom_rejects_builtin_name(tmp_path):
    settings_file = tmp_path / "settings.json"
    with pytest.raises(ValueError, match="built-in"):
        add_formation("3-3-1", ["RB", "CB", "LB"], ["RM", "CM", "LM"], ["FW"], str(settings_file))


def test_get_formation_falls_back_to_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    assert get_formation(str(settings_file)) == DEFAULT_FORMATION


def test_set_formation_custom_and_current(tmp_path):
    settings_file = tmp_path / "settings.json"
    add_formation("3-0-4x", ["RB", "CB", "LB"], [], ["RM", "CM", "FW", "LM"], str(settings_file))
    set_formation("3-0-4x", str(settings_file))
    assert get_formation(str(settings_file)) == "3-0-4x"


def test_render_pitch_custom_formation(tmp_path):
    settings_file = tmp_path / "settings.json"
    add_formation("2-4-1x", ["CB", "RB"], ["CM", "RM", "LM", "LB"], ["FW"], str(settings_file))
    team = {pos: f"P_{pos}" for pos in ALL_POSITIONS}
    pitch = render_pitch(team, "2-4-1x", str(settings_file))
    assert "FW: P_FW" in pitch
    assert "CB: P_CB" in pitch
    assert "RB: P_RB" in pitch