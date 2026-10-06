"""Draw history: tracks how often each player lands on Team A, persisted to JSON.

Used by the fairness logic so that over many draws every player gets a similar
number of Team A / Team B appearances.
"""

import datetime
import json
import logging
import os

logger = logging.getLogger(__name__)

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "draw_history.json")


def load_history(path: str | None = None) -> dict:
    """Read draw history from disk, or return an empty structure if absent/corrupt."""
    path = path or HISTORY_FILE
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("counts"), dict):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read draw history %s", path)
    return {"counts": {}, "draws": []}


def save_history(history: dict, path: str | None = None) -> None:
    """Write the draw history to disk."""
    path = path or HISTORY_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def team_a_counts(path: str | None = None) -> dict[str, int]:
    """Return {player: number of times drawn on Team A}."""
    return load_history(path).get("counts", {})


def record_draw(
    team_a: dict[str, str],
    team_b: dict[str, str],
    path: str | None = None,
) -> dict:
    """Register a completed draw: bump Team A counts and append the lineup."""
    history = load_history(path)
    counts = history["counts"]
    for player in team_a.values():
        counts[player] = counts.get(player, 0) + 1
    history["draws"].append(
        {
            "team_a": team_a,
            "team_b": team_b,
            "at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_history(history, path)
    return history


def latest_draw(path: str | None = None) -> dict | None:
    """Return the most recent draw's lineups (used to record match results)."""
    draws = load_history(path).get("draws", [])
    return draws[-1] if draws else None