"""Pure team-generation logic (no Telegram dependencies here, so it is easy to test)."""

import itertools
import random

from players import PLAYERS

# Canonical position order used for a stable, readable output.
POSITION_ORDER = list(PLAYERS.keys())


def generate_teams(
    team_a_counts: dict[str, int] | None = None,
    strengths: dict[str, int] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return two fair teams (Team A, Team B).

    For each position exactly one of its two players goes to Team A and the other
    to Team B, so every team has one player per position and the two players of
    a position never meet.

    Priority of the balancing strategy:
    1. If a ``strengths`` dict is given (player -> total strength value), pick
       the assignment (over the 2^8 possible) whose two teams have the most
       similar total strength. Ties are broken randomly so draws still vary.
    2. Else, if ``team_a_counts`` is given, bias toward putting the player who
       has been on Team A less often onto Team A (long-run balance).
    3. Otherwise fall back to plain random shuffle per position.
    """
    positions = POSITION_ORDER
    pairs = [PLAYERS[pos] for pos in positions]

    if strengths:
        best_diff = None
        best_bit_patterns: list[tuple[int, ...]] = []
        for bits in itertools.product([0, 1], repeat=len(positions)):
            a = sum(strengths[pairs[i][bits[i]]] for i in range(len(positions)))
            b = sum(strengths[pairs[i][1 - bits[i]]] for i in range(len(positions)))
            diff = abs(a - b)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_bit_patterns = [bits]
            elif diff == best_diff:
                best_bit_patterns.append(bits)
        bits = random.choice(best_bit_patterns)
        team_a, team_b = {}, {}
        for i, position in enumerate(positions):
            if bits[i] == 0:
                team_a[position], team_b[position] = pairs[i][0], pairs[i][1]
            else:
                team_a[position], team_b[position] = pairs[i][1], pairs[i][0]
        return team_a, team_b

    team_a: dict[str, str] = {}
    team_b: dict[str, str] = {}

    for position in positions:
        p1, p2 = PLAYERS[position]

        if team_a_counts:
            a1 = team_a_counts.get(p1, 0)
            a2 = team_a_counts.get(p2, 0)
            if a1 != a2:
                if a1 < a2:
                    team_a[position], team_b[position] = p1, p2
                else:
                    team_a[position], team_b[position] = p2, p1
                continue

        pair = [p1, p2]
        random.shuffle(pair)
        team_a[position], team_b[position] = pair[0], pair[1]

    return team_a, team_b


def team_strength(team: dict[str, str], strengths: dict[str, int]) -> int:
    """Total strength of a team from the pre-computed strengths dict."""
    return sum(strengths.get(player, 0) for player in team.values())


def win_probability(
    team_a: dict[str, str], team_b: dict[str, str], strengths: dict[str, int]
) -> tuple[int, int]:
    """Two-way win probability (percentages summing to 100) from team strength."""
    a = team_strength(team_a, strengths)
    b = team_strength(team_b, strengths)
    if a + b == 0:
        return 50, 50
    p_a = round(a / (a + b) * 100)
    return p_a, 100 - p_a


def format_teams(team_a: dict[str, str], team_b: dict[str, str]) -> str:
    """Render the two teams as a Telegram Markdown formatted message."""
    lines = ["⚽ *Match Teams* ⚽", "", "🟩 *Team A*"]
    lines.extend(f"{position} — {team_a[position]}" for position in POSITION_ORDER)
    lines.append("")
    lines.append("🟥 *Team B*")
    lines.extend(f"{position} — {team_b[position]}" for position in POSITION_ORDER)
    return "\n".join(lines)
