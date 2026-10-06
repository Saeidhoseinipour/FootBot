"""Weekly goals/assists statistics, persisted to a JSON file on disk.

All functions accept an optional ``path`` so they stay pure and easy to test
with pytest (a temp file), while the bot uses the default ``stats.json``.
"""

import json
import os

from players import PLAYERS

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")

RECORD_USAGE = (
    "Usage: `/record <week> Player:goals:assists,Player:goals:assists`\n\n"
    "Example:\n`/record 3 Sahand:2:1,Hani:1:2,Saeed:0:1`"
)

RESULT_USAGE = (
    "Usage: `/result <week> <scoreA>:<scoreB>`\n\n"
    "Example:\n`/result 3 4:2`  (Team A won 4–2)"
)


def load_stats(path: str | None = None) -> dict:
    """Read stats from disk, or return an empty structure if absent/corrupt."""
    path = path or STATS_FILE
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("weeks"), dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"weeks": {}}


def save_stats(stats: dict, path: str | None = None) -> None:
    """Write the stats structure to disk."""
    path = path or STATS_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def set_week_record(
    week: int, records: list[tuple[str, int, int]], path: str | None = None
) -> dict:
    """Store one week's records: a list of (player, goals, assists).

    Recording the same week again overwrites its previous data.
    """
    goals: dict[str, int] = {}
    assists: dict[str, int] = {}
    for player, goals_count, assists_count in records:
        goals[player] = goals_count
        assists[player] = assists_count

    stats = load_stats(path)
    stats["weeks"][str(week)] = {"goals": goals, "assists": assists}
    save_stats(stats, path)
    return stats


def get_week_record(week: int, path: str | None = None) -> dict | None:
    """Return {'goals': {...}, 'assists': {...}} for a week, or None."""
    stats = load_stats(path)
    return stats["weeks"].get(str(week))


def aggregate_stats(stats: dict | None = None) -> dict[str, dict[str, int]]:
    """Sum goals/assists per player across every recorded week.

    Returns {"player": {"goals": n, "assists": m}}.
    """
    stats = stats or load_stats()
    totals: dict[str, dict[str, int]] = {}
    for week in stats.get("weeks", {}).values():
        for player, count in week.get("goals", {}).items():
            totals.setdefault(player, {"goals": 0, "assists": 0})["goals"] += count
        for player, count in week.get("assists", {}).items():
            totals.setdefault(player, {"goals": 0, "assists": 0})["assists"] += count
    return totals


def parse_record_input(text: str, valid_players: set[str]) -> tuple[int, list[tuple[str, int, int]]]:
    """Parse a /record command line into (week, [(player, goals, assists), ...]).

    Raises ValueError with a human-readable message on invalid input.
    """
    tokens = text.strip().split(maxsplit=1)
    if len(tokens) < 2:
        raise ValueError("No week given.")

    parts = tokens[1].split(None, 1)
    try:
        week = int(parts[0])
    except (IndexError, ValueError):
        raise ValueError("The week must be a number, e.g. `/record 3 ...`.")
    if week <= 0:
        raise ValueError("The week must be a positive number.")

    entries_text = parts[1].strip() if len(parts) > 1 else ""
    if not entries_text:
        raise ValueError("No entries given.")

    records: list[tuple[str, int, int]] = []
    for entry in entries_text.split(","):
        entry = entry.strip()
        if not entry:
            continue
        fields = [field.strip() for field in entry.split(":")]
        if len(fields) != 3:
            raise ValueError(f"Bad entry '{entry}'. Use Player:goals:assists.")
        player, goals_text, assists_text = fields
        if player not in valid_players:
            raise ValueError(
                f"Unknown player '{player}'. Use /players to see exact names."
            )
        try:
            goals, assists = int(goals_text), int(assists_text)
        except ValueError:
            raise ValueError(f"Goals/assists must be numbers in '{entry}'.")
        if goals < 0 or assists < 0:
            raise ValueError("Goals and assists cannot be negative.")
        records.append((player, goals, assists))

    if not records:
        raise ValueError("No valid entries given.")
    return week, records


def format_overall_stats(totals: dict[str, dict[str, int]]) -> str:
    """Render aggregate totals as ranked goal/assist lists (best first)."""
    if not totals:
        return (
            "📊 *Overall Statistics*\n\n"
            "No goals or assists recorded yet. Use /record to add some."
        )

    active = [kv for kv in totals.items() if kv[1]["goals"] > 0 or kv[1]["assists"] > 0]
    if not active:
        return "📊 *Overall Statistics*\n\nNo goals or assists recorded yet."

    goals_list, assists_list = ranked_totals(totals)

    lines = ["📊 *Overall Statistics*", ""]
    lines.append("*Goals* ⚽")
    if goals_list:
        lines.extend(
            f"{i}. {player} — {counts['goals']}"
            for i, (player, counts) in enumerate(goals_list, start=1)
        )
    else:
        lines.append("No goals recorded yet.")
    lines.append("")
    lines.append("*Assists* 👟")
    if assists_list:
        lines.extend(
            f"{i}. {player} — {counts['assists']}"
            for i, (player, counts) in enumerate(assists_list, start=1)
        )
    else:
        lines.append("No assists recorded yet.")
    return "\n".join(lines)


def ranked_totals(totals: dict[str, dict[str, int]]) -> tuple[list, list]:
    """Split totals into ranked goals and assists lists (best first, count > 0).

    Returns ([(player, {'goals': n, 'assists': m}), ...], [...]).
    """
    active = [
        kv for kv in totals.items() if kv[1]["goals"] > 0 or kv[1]["assists"] > 0
    ]
    goals_list = [
        kv
        for kv in sorted(active, key=lambda kv: (-kv[1]["goals"], -kv[1]["assists"], kv[0]))
        if kv[1]["goals"] > 0
    ]
    assists_list = [
        kv
        for kv in sorted(active, key=lambda kv: (-kv[1]["assists"], -kv[1]["goals"], kv[0]))
        if kv[1]["assists"] > 0
    ]
    return goals_list, assists_list


def format_week_stats(week_data: dict, week: int) -> str:
    """Render the goals/assists of a single week."""
    goals = week_data.get("goals", {})
    assists = week_data.get("assists", {})
    lines = [f"📊 *Week {week} Statistics*", ""]

    lines.append("*Goals* ⚽")
    if goals:
        lines.extend(
            f"{player} — {count}"
            for player, count in sorted(goals.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    else:
        lines.append("No goals recorded.")
    lines.append("")
    lines.append("*Assists* 👟")
    if assists:
        lines.extend(
            f"{player} — {count}"
            for player, count in sorted(assists.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    else:
        lines.append("No assists recorded.")
    return "\n".join(lines)


def set_result(
    week: int,
    score_a: int,
    score_b: int,
    team_a: dict[str, str],
    team_b: dict[str, str],
    path: str | None = None,
) -> dict:
    """Store a week's match result together with the lineups that played.

    Recording the same week again overwrites its previous result.
    """
    stats = load_stats(path)
    results = stats.setdefault("results", {})
    results[str(week)] = {
        "score_a": int(score_a),
        "score_b": int(score_b),
        "team_a": team_a,
        "team_b": team_b,
    }
    save_stats(stats, path)
    return stats


def get_result(week: int, path: str | None = None) -> dict | None:
    """Return the recorded result dict for a week, or None."""
    return load_stats(path).get("results", {}).get(str(week))


def player_records(stats: dict | None = None) -> dict[str, dict[str, int]]:
    """Aggregate wins/losses/draws/games per player from all recorded results.

    Returns {"player": {"wins": n, "losses": n, "draws": n, "games": n}}.
    """
    stats = stats or load_stats()
    records: dict[str, dict[str, int]] = {}
    for result in stats.get("results", {}).values():
        score_a, score_b = result["score_a"], result["score_b"]
        teams = [result["team_a"], result["team_b"]]
        scores = [score_a, score_b]
        for team, score in zip(teams, scores):
            if score_a == score_b:
                outcome = "draws"
            else:
                outcome = "wins" if score == max(scores) else "losses"
            for player in team.values():
                rec = records.setdefault(
                    player, {"wins": 0, "losses": 0, "draws": 0, "games": 0}
                )
                rec[outcome] += 1
                rec["games"] += 1
    return records


def format_player_table(stats: dict | None = None) -> str:
    """Render a full player table: rank, position, goals, assists, W/L/P, win%.

    Ranked best-to-worst by win percentage, then goals, then assists.
    """
    stats = stats or load_stats()
    totals = aggregate_stats(stats)
    records = player_records(stats)
    position_of = {player: pos for pos, pair in PLAYERS.items() for player in pair}

    rows: list[tuple[str, int, int, int, int, int, float]] = []
    for player in {p for pair in PLAYERS.values() for p in pair}:
        g = totals.get(player, {}).get("goals", 0)
        a = totals.get(player, {}).get("assists", 0)
        rec = records.get(player, {"wins": 0, "losses": 0, "draws": 0, "games": 0})
        games = rec["games"]
        win_pct = (rec["wins"] / games * 100) if games else 0.0
        rows.append((player, g, a, rec["wins"], rec["losses"], games, win_pct))

    rows.sort(key=lambda r: (-r[6], -r[3], -r[1], -r[2], r[0]))

    name_width = max(len(r[0]) for r in rows)
    lines = ["📊 *Player Table*"]
    header = (
        f"{'Rank':<4} {'Player':<{name_width}} {'Pos':<3} "
        f"{'G':>2} {'A':>2} {'W':>2} {'L':>2} {'P':>2} {'W%':>4}"
    )
    lines.append(f"`{header}`")
    for rank, (player, g, a, w, l, p, pct) in enumerate(rows, start=1):
        pos = position_of[player]
        pct_str = f"{pct:.0f}%"
        row = (
            f"{rank:<4} {player:<{name_width}} {pos:<3} "
            f"{g:>2} {a:>2} {w:>2} {l:>2} {p:>2} {pct_str:>4}"
        )
        lines.append(f"`{row}`")
    lines.append("")
    lines.append("G = goals · A = assists · W = wins · L = losses · P = games")
    return "\n".join(lines)