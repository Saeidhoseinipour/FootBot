"""Configurable tactical formations and schematic (pitch) rendering.

A formation partitions the 8 fixed positions into field lines, e.g. the
3-3-1 = Defense (RB CB LB), Midfield (RM CM LM), Attack (FW) plus the GK.
Built-in formations live in ``FORMATIONS``; users can add more at runtime with
``/formation add`` — those are stored in settings.json and validated to use
every position exactly once.
"""

import json
import logging
import os

from players import PLAYERS

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
DEFAULT_FORMATION = "3-3-1"

# Each formation uses every position exactly once.
FORMATIONS: dict[str, dict[str, list[str]]] = {
    "3-3-1": {
        "Attack": ["FW"],
        "Midfield": ["RM", "CM", "LM"],
        "Defense": ["RB", "CB", "LB"],
        "Goalkeeper": ["GK"],
    },
    "3-2-2": {
        "Attack": ["FW", "LM"],
        "Midfield": ["CM", "RM"],
        "Defense": ["RB", "CB", "LB"],
        "Goalkeeper": ["GK"],
    },
    "3-1-3": {
        "Attack": ["RM", "FW", "LM"],
        "Midfield": ["CM"],
        "Defense": ["RB", "CB", "LB"],
        "Goalkeeper": ["GK"],
    },
    "3-0-4": {
        "Attack": ["RM", "CM", "FW", "LM"],
        "Midfield": [],
        "Defense": ["RB", "CB", "LB"],
        "Goalkeeper": ["GK"],
    },
    "2-3-2": {
        "Attack": ["FW", "LM"],
        "Midfield": ["CM", "RM", "LB"],
        "Defense": ["CB", "RB"],
        "Goalkeeper": ["GK"],
    },
    "2-4-1": {
        "Attack": ["FW"],
        "Midfield": ["CM", "RM", "LM", "LB"],
        "Defense": ["CB", "RB"],
        "Goalkeeper": ["GK"],
    },
}

# Rows are drawn from the bottom of the pitch (GK) to the top (Attack).
LINE_ORDER = ["Goalkeeper", "Defense", "Midfield", "Attack"]


def _validate_formations() -> None:
    """Ensure every built-in formation uses all 8 positions exactly once."""
    expected = set(PLAYERS.keys())
    for name, lines in FORMATIONS.items():
        used = [pos for positions in lines.values() for pos in positions]
        if set(used) != expected or len(used) != len(expected):
            raise ValueError(f"Formation '{name}' does not use all positions: {used}")
    if DEFAULT_FORMATION not in FORMATIONS:
        raise ValueError(f"DEFAULT_FORMATION '{DEFAULT_FORMATION}' is not defined")


_validate_formations()


def load_settings(settings_file: str | None = None) -> dict:
    """Read settings.json, or an empty dict if absent/corrupt."""
    settings_file = settings_file or SETTINGS_FILE
    if os.path.exists(settings_file):
        try:
            with open(settings_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read settings %s", settings_file)
    return {}


def save_settings(data: dict, settings_file: str | None = None) -> None:
    settings_file = settings_file or SETTINGS_FILE
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_custom_formations(settings_file: str | None = None) -> dict:
    """Return user-defined formations added via /formation add."""
    return load_settings(settings_file).get("custom_formations", {})


def all_formations(settings_file: str | None = None) -> dict[str, dict[str, list[str]]]:
    """Built-in formations merged with custom ones (custom wins on name clash)."""
    merged = dict(FORMATIONS)
    merged.update(get_custom_formations(settings_file))
    return merged


def _parse_custom_lines(
    defense: list[str], midfield: list[str], attack: list[str]
) -> dict[str, list[str]]:
    """Validate three outfield lines and build the formation structure."""
    lines = {
        "Defense": [pos.upper().strip() for pos in defense],
        "Midfield": [pos.upper().strip() for pos in midfield],
        "Attack": [pos.upper().strip() for pos in attack],
        "Goalkeeper": ["GK"],
    }
    # used includes GK (always added above), so compare against ALL positions.
    expected = set(PLAYERS.keys())
    used = [pos for positions in lines.values() for pos in positions]
    if set(used) != expected or len(used) != len(expected):
        missing = expected - set(used)
        raise ValueError(
            f"Formation must use all 8 positions once. "
            f"Missing: {sorted(missing) or 'none'}, duplicates/extra present."
        )
    return lines


def add_formation(
    name: str,
    defense: list[str],
    midfield: list[str],
    attack: list[str],
    settings_file: str | None = None,
) -> str:
    """Register a custom formation. Raises ValueError if invalid."""
    if name in FORMATIONS:
        raise ValueError(f"'{name}' is already a built-in formation.")
    lines = _parse_custom_lines(defense, midfield, attack)
    data = load_settings(settings_file)
    customs = data.setdefault("custom_formations", {})
    customs[name] = lines
    save_settings(data, settings_file)
    return name


def get_formation(settings_file: str | None = None) -> str:
    """Return the current formation name (default 3-3-1)."""
    data = load_settings(settings_file)
    name = data.get("formation")
    if name in all_formations(settings_file):
        return name
    return DEFAULT_FORMATION


def get_rating_mode(settings_file: str | None = None) -> str:
    """Return the current rating mode: '5skill', '2skill', or 'performance'."""
    data = load_settings(settings_file)
    mode = data.get("rating_mode", "5skill")
    return mode if mode in ("5skill", "2skill", "performance") else "5skill"


def set_rating_mode(mode: str, settings_file: str | None = None) -> str:
    """Persist the current rating mode. Raises ValueError for unknown modes."""
    valid = ("5skill", "2skill", "performance")
    if mode not in valid:
        raise ValueError(f"Unknown rating mode '{mode}'. Choose from: {', '.join(valid)}")
    data = load_settings(settings_file)
    data["rating_mode"] = mode
    save_settings(data, settings_file)
    return mode


def set_formation(name: str, settings_file: str | None = None) -> str:
    """Persist the current formation. Raises ValueError for unknown names."""
    if name not in all_formations(settings_file):
        raise ValueError(
            f"Unknown formation '{name}'. Use /formations to see available ones."
        )
    data = load_settings(settings_file)
    data["formation"] = name
    save_settings(data, settings_file)
    return name


def render_pitch(team: dict[str, str], formation_name: str, settings_file: str | None = None) -> str:
    """Render one team as an ASCII pitch diagram (use inside a code block)."""
    all_f = all_formations(settings_file)
    if formation_name not in all_f:
        raise ValueError(f"Unknown formation '{formation_name}'.")
    formation = all_f[formation_name]
    rows = []
    for line_name in LINE_ORDER:
        positions = formation[line_name]
        if not positions:
            continue
        rows.append("    ".join(f"{pos}: {team[pos]}" for pos in positions))

    width = max(len(row) for row in rows)
    border = "─" * (width + 2)
    out = ["┌" + border + "┐"]
    out.extend("│ " + row.center(width) + " │" for row in rows)
    out.append("└" + border + "┘")
    return "\n".join(out)


def format_formation_team(
    team: dict[str, str],
    formation_name: str,
    team_label: str,
    settings_file: str | None = None,
) -> str:
    """Full schematic message for one team (Markdown code-block diagram)."""
    lines = [f"⚽ *{team_label} — {formation_name}* ⚽"]
    lines.extend(f"`{row}`" for row in render_pitch(team, formation_name, settings_file).split("\n"))
    return "\n".join(lines)