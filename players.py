"""Fixed player pool: exactly 2 players per position across 8 positions."""

# Note: "Mohammd Hosein" (GK) and "Mohammad" (LM) are two different players,
# and "Saeed" (CB) and "Saeid" (CM) are two different players.
# Keep the spellings exactly as written below.
PLAYERS: dict[str, list[str]] = {
    "GK": ["Mohammd Hosein", "Hani"],
    "CB": ["Saeed", "Amin"],
    "RB": ["Mehrdad", "Abasi"],
    "LB": ["Mehrzad", "Amir"],
    "CM": ["Nima", "Saeid"],
    "RM": ["Milad", "Kazemi"],
    "FW": ["Sahand", "Navid"],
    "LM": ["Mohammad", "Ali"],
}