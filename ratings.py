"""Player skill ratings: three rating modes, persisted to JSON.

Mode "5skill": Dribbling, Passing, Finishing, Pace, Defending (1-10 each).
Mode "2skill": Attacking, Defending (1-10 each).
Mode "performance": auto-computed from goals/assists recorded via /record.

The active mode is stored in settings.json ("rating_mode" key).
"""

import json
import logging
import os

from players import PLAYERS

logger = logging.getLogger(__name__)

RATINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ratings.json")
RATINGS2_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ratings2.json")

SKILLS = ["Dribbling", "Passing", "Finishing", "Pace", "Defending"]
SKILLS_2 = ["Attacking", "Defending"]

ALL_PLAYER_NAMES = {player for pair in PLAYERS.values() for player in pair}

RATE_USAGE = (
    "Usage: `/rate <player> dribbling passing finishing pace defending`\n\n"
    "Each value is 1-10. Example:\n`/rate Sahand 8 6 9 7 5`"
)

RATE2_USAGE = (
    "Usage: `/rate2 <player> attacking defending`\n\n"
    "Each value is 1-10. Example:\n`/rate2 Sahand 8 5`"
)


# ---------------------------------------------------------------------------
# 5-skill ratings
# ---------------------------------------------------------------------------

def load_ratings(path: str | None = None) -> dict:
    path = path or RATINGS_FILE
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read ratings %s", path)
    return {}


def save_ratings(ratings: dict, path: str | None = None) -> None:
    path = path or RATINGS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ratings, f, ensure_ascii=False, indent=2)


def set_player_skills(player: str, values: dict[str, int], path: str | None = None) -> None:
    if set(values.keys()) != set(SKILLS):
        raise ValueError(f"Provide exactly these skills: {', '.join(SKILLS)}")
    for skill, value in values.items():
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Skill '{skill}' must be a number 1-10.")
        if not 1 <= value <= 10:
            raise ValueError(f"Skill '{skill}' must be between 1 and 10.")
    ratings = load_ratings(path)
    ratings[player] = {skill: int(values[skill]) for skill in SKILLS}
    save_ratings(ratings, path)


def get_all_ratings(path: str | None = None) -> dict:
    return load_ratings(path)


def is_complete(ratings: dict | None = None) -> bool:
    ratings = ratings or load_ratings()
    if not ratings:
        return False
    return all(
        player in ratings
        and isinstance(ratings[player], dict)
        and all(skill in ratings[player] for skill in SKILLS)
        for player in ALL_PLAYER_NAMES
    )


def reset_ratings(path: str | None = None) -> None:
    save_ratings({}, path)


def format_ratings_table(ratings: dict | None = None) -> str:
    ratings = ratings or load_ratings()
    if not ratings:
        return "🏅 *5-Skill Ratings*\n\nNo ratings yet. Use /rate to add some."
    lines = ["🏅 *5-Skill Ratings*", ""]
    header = f"{'Player':<16}" + "".join(f"{s[:4]:>6}" for s in SKILLS)
    lines.append(f"`{header}`")
    for player in ALL_PLAYER_NAMES:
        row = f"{player:<16}"
        r = ratings.get(player)
        if r:
            row += "".join(f"{r[skill]:>6}" for skill in SKILLS)
        else:
            row += f"{'--':>6}" * len(SKILLS)
        lines.append(f"`{row}`")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2-skill ratings (Attacking / Defending)
# ---------------------------------------------------------------------------

def load_ratings2(path: str | None = None) -> dict:
    path = path or RATINGS2_FILE
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read ratings2 %s", path)
    return {}


def save_ratings2(ratings: dict, path: str | None = None) -> None:
    path = path or RATINGS2_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ratings, f, ensure_ascii=False, indent=2)


def set_player_skills_2(player: str, values: dict[str, int], path: str | None = None) -> None:
    if set(values.keys()) != set(SKILLS_2):
        raise ValueError(f"Provide exactly: {', '.join(SKILLS_2)}")
    for skill, value in values.items():
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Skill '{skill}' must be a number 1-10.")
        if not 1 <= value <= 10:
            raise ValueError(f"Skill '{skill}' must be between 1 and 10.")
    ratings = load_ratings2(path)
    ratings[player] = {skill: int(values[skill]) for skill in SKILLS_2}
    save_ratings2(ratings, path)


def get_all_ratings2(path: str | None = None) -> dict:
    return load_ratings2(path)


def is_complete_2(ratings: dict | None = None) -> bool:
    ratings = ratings or load_ratings2()
    if not ratings:
        return False
    return all(
        player in ratings
        and isinstance(ratings[player], dict)
        and all(skill in ratings[player] for skill in SKILLS_2)
        for player in ALL_PLAYER_NAMES
    )


def reset_ratings2(path: str | None = None) -> None:
    save_ratings2({}, path)


def format_ratings_table_2(ratings: dict | None = None) -> str:
    ratings = ratings or load_ratings2()
    if not ratings:
        return "🏅 *2-Skill Ratings*\n\nNo ratings yet. Use /rate2 to add some."
    lines = ["🏅 *2-Skill Ratings*", ""]
    header = f"{'Player':<16}" + "".join(f"{s[:4]:>6}" for s in SKILLS_2)
    lines.append(f"`{header}`")
    for player in ALL_PLAYER_NAMES:
        row = f"{player:<16}"
        r = ratings.get(player)
        if r:
            row += "".join(f"{r[skill]:>6}" for skill in SKILLS_2)
        else:
            row += f"{'--':>6}" * len(SKILLS_2)
        lines.append(f"`{row}`")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Performance ratings (auto from goals / assists)
# ---------------------------------------------------------------------------

def performance_score(player: str, stats: dict | None = None) -> int:
    """Compute a performance score: each goal = 3 pts, each assist = 2 pts."""
    from stats import aggregate_stats, load_stats

    stats = stats or load_stats()
    totals = aggregate_stats(stats)
    g = totals.get(player, {}).get("goals", 0)
    a = totals.get(player, {}).get("assists", 0)
    return g * 3 + a * 2


# ---------------------------------------------------------------------------
# Unified strength builder (used by logic.py for balanced draws)
# ---------------------------------------------------------------------------

def build_strengths(
    mode: str,
    ratings_5: dict | None = None,
    ratings_2: dict | None = None,
    stats: dict | None = None,
) -> dict[str, int] | None:
    """Build {player: total_strength} for the given mode.

    Returns None when ratings are incomplete (caller should fallback).
    """
    all_players = ALL_PLAYER_NAMES

    if mode == "5skill" and ratings_5 and is_complete(ratings_5):
        return {p: sum(ratings_5[p][s] for s in SKILLS) for p in all_players}

    if mode == "2skill" and ratings_2 and is_complete_2(ratings_2):
        return {p: sum(ratings_2[p][s] for s in SKILLS_2) for p in all_players}

    if mode == "performance":
        strengths = {p: performance_score(p, stats) for p in all_players}
        if any(v > 0 for v in strengths.values()):
            return strengths

    return None
