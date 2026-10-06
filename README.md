# Football Team Randomizer ⚽

A Telegram bot that generates two fair 8v8 football teams from a fixed pool of
16 players (2 players per position across 8 positions).

For each position, one of the two players is randomly assigned to **Team A**
(green 🟩) and the other to **Team B** (red 🟥), so both teams always have
exactly one player per position (GK, CB, RB, LB, CM, RM, FW, LM).

It also tracks weekly goals and assists per player, shows overall statistics,
and can display player photos in the draw and statistics.

## Commands

- `/start` — welcome message and command list
- `/players` — show the full player pool grouped by position
- `/draw` — generate two new random teams (with a **🔄 Re-draw** inline button)
- `/record <week> Player:goals:assists,...` — save a week's goals and assists,
  e.g. `/record 3 Sahand:2:1,Hani:1:2`
- `/result <week> <scoreA>:<scoreB>` — save a week's match score (uses the most
  recent draw as the lineups), e.g. `/result 3 4:2`
- `/stats` — overall goals ⚽ and assists 👟 per player across all weeks
- `/table` — full player table ranked by win %: rank, position, goals,
  assists, wins, losses, games
- `/week <n>` — goals and assists of a specific week
- `/history` — team balance across all draws (Team A vs Team B per player)
- `/tactic` — draw teams shown as a schematic pitch in the current formation
- `/formation <name>` — set the formation (e.g. `3-3-1`, `3-2-2`, `3-1-3`,
  `3-0-4`, `2-3-2`, `2-4-1`)
- `/formation add <name> D / M / A` — create a custom formation, e.g.
  `/formation add 2-3-2 CB,RB / CM,RM,LM / FW,LB`
- `/formations` — list available formations (built-in + custom) and current

Formations are configurable; each one must use all 8 positions exactly once
(validated at add time). Built-ins live in `formations.py`, customs are stored
in `settings.json`, and the default is `3-3-1`.
- `/ratemode` — show or set the rating mode: `5skill`, `2skill`, or `performance`
- `/rate <player> d p f pa de` — set a player's 5 skill ratings (1-10 each)
- `/rates` — show all 5-skill ratings
- `/resetrates` — clear all 5-skill ratings
- `/rate2 <player> attacking defending` — set a player's 2 skill ratings (1-10)
- `/rates2` — show all 2-skill ratings
- `/resetrates2` — clear all 2-skill ratings
- `/setphoto` — upload a photo for a player: send a photo with the caption
  `/setphoto <player name>`
- `/removephoto <player name>` — delete a player's photo

`/record`, `/result`, `/setphoto` and `/removephoto` are **admin-only**: set the
allowed Telegram user IDs with `ADMIN_IDS=123456789,...` in `.env`. If
`ADMIN_IDS` is empty, everyone can use them.

Draws are **balanced over time**: the player who has been on Team A less often
is more likely to be drawn into Team A, so over many draws every player gets a
similar number of Team A / Team B appearances. See `/history`.

**Rating modes** control how teams are balanced by skill. Use `/ratemode` to switch:

- `5skill` — manual ratings with `/rate` (Dribbling, Passing, Finishing, Pace, Defending)
- `2skill` — manual ratings with `/rate2` (Attacking, Defending)
- `performance` — automatic from goals/assists recorded via `/record` (goals × 3 + assists × 2)

When the chosen mode has complete ratings, `/draw` and `/tactic` show team
strength and win probability. When ratings are incomplete, the bot falls back
to history-based fairness balancing.

Match results feed the **player table** (`/table`): each player's win
percentage is computed from the results of the weeks their team won. Ranking is
best-to-worst by win %, then goals, then assists.

Weekly records are stored in `stats.json`. Draw history is stored in
`draw_history.json`. Uploaded player photos are stored in `player_photos/`. On
`/draw` and `/stats`, the bot also sends albums of player photos (players
without a photo are skipped).

## Setup

1. Create a bot and get its token from [@BotFather](https://t.me/BotFather).
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create your environment file:

   ```bash
   copy .env.example .env
   ```

   then open `.env` and set your real `BOT_TOKEN`.

> If your network can't reach `api.telegram.org` (slow VPN, filtered network),
> the bot already uses generous 30s timeouts. You can also route through a
> proxy by setting `PROXY=http://127.0.0.1:PORT` (or `socks5://...`) in `.env`.

## Run

```bash
python main.py
```

The bot will start polling for updates. Send `/start` to your bot in Telegram.

## Tests

Run the pure logic tests (no bot token needed):

```bash
pytest
```

The tests verify that every draw produces two teams of 8, with exactly one
player per position per team, and that the two players of a position are never
on the same team. Stats tests cover saving weeks, aggregating totals and
validating `/record` input.

## Project structure

```
main.py        # entry point: loads token, registers handlers, starts polling
handlers.py    # Telegram commands (/start, /players, /draw, /record, /stats, etc.)
logic.py       # pure, testable team-generation logic
players.py     # fixed player pool (data)
stats.py       # weekly goals/assists storage + aggregation (JSON)
photos.py      # player photo storage (player_photos/ + index.json)
ratings.py     # skill ratings (5-skill, 2-skill, performance mode)
draw_history.py# draw history + fairness tracking (draw_history.json)
formations.py  # tactical formations + schematic pitch renderer (settings.json)
stats.json     # created automatically when the first record is saved
player_photos/ # created automatically when the first photo is uploaded
draw_history.json # created automatically on the first /draw
settings.json  # stores the current formation + rating mode
ratings.json   # 5-skill ratings storage
ratings2.json  # 2-skill ratings storage
test_logic.py  # pytest tests for the generation logic
test_stats.py  # pytest tests for the stats logic
test_photos.py # pytest tests for the photo storage logic
test_fairness.py   # pytest tests for balanced draws + draw history
test_formations.py # pytest tests for formations + pitch rendering
test_ratings.py    # pytest tests for ratings + skill balancing
```