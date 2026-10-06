"""Telegram bot handlers: /start, /players, /draw, /record, /stats, /week, /setphoto."""

import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, filters

from draw_history import latest_draw, load_history, record_draw, team_a_counts
from formations import (
    FORMATIONS,
    add_formation,
    all_formations,
    format_formation_team,
    get_custom_formations,
    get_formation,
    get_rating_mode,
    set_formation,
    set_rating_mode,
)
from logic import POSITION_ORDER, format_teams, generate_teams, team_strength, win_probability
from photos import get_photo_path, remove_photo, set_photo
from players import PLAYERS
from ratings import (
    RATE_USAGE,
    RATE2_USAGE,
    SKILLS,
    SKILLS_2,
    build_strengths,
    format_ratings_table,
    format_ratings_table_2,
    get_all_ratings,
    get_all_ratings2,
    is_complete,
    is_complete_2,
    performance_score,
    reset_ratings,
    reset_ratings2,
    set_player_skills,
    set_player_skills_2,
)
from stats import (
    RECORD_USAGE,
    RESULT_USAGE,
    aggregate_stats,
    format_overall_stats,
    format_player_table,
    format_week_stats,
    get_week_record,
    load_stats,
    parse_record_input,
    ranked_totals,
    set_result,
    set_week_record,
)
from stats import (
    RECORD_USAGE,
    RESULT_USAGE,
    aggregate_stats,
    format_overall_stats,
    format_player_table,
    format_week_stats,
    get_week_record,
    parse_record_input,
    ranked_totals,
    set_result,
    set_week_record,
)

logger = logging.getLogger(__name__)

RE_DRAW_CALLBACK = "redraw"
RE_DRAW_TACTIC_CALLBACK = "redraw_tactic"

ALL_PLAYER_NAMES = {player for pair in PLAYERS.values() for player in pair}

WELCOME_TEXT = (
    "👋 Welcome to *Football Team Randomizer*!\n\n"
    "I organize your 8v8 football matches with 16 fixed players.\n\n"
    "Commands:\n"
    "• /players — show the player pool grouped by position\n"
    "• /draw — generate two fresh, fair teams (with player photos)\n"
    "• /record — save weekly goals and assists\n"
    "• /result — save a week's match score\n"
    "• /stats — overall goals/assists per player\n"
    "• /table — full player table ranked by win % (G, A, W, L, P)\n"
    "• /week <n> — statistics of a specific week\n"
    "• /history — team balance across all draws\n"
    "• /tactic — draw teams shown as a schematic pitch (3-3-1 by default)\n"
    "• /formation — set the formation (e.g. 3-3-1, 3-2-2, 3-1-3)\n"
    "• /formations — list available formations\n"
    "• /ratemode — show or set the rating mode\n"
    "• /rate — set a player's 5 skill ratings (1-10)\n"
    "• /rates — show all 5-skill ratings\n"
    "• /resetrates — clear all 5-skill ratings\n"
    "• /rate2 — set a player's 2 skill ratings (1-10)\n"
    "• /rates2 — show all 2-skill ratings\n"
    "• /resetrates2 — clear all 2-skill ratings\n"
    "• /setphoto — set a player's photo\n"
    "• /removephoto — remove a player's photo\n\n"
    "How the draw works: for each position one of the two players is randomly "
    "assigned to Team A (green) and the other to Team B (red), so both teams "
    "always have one player per position. Draws also stay balanced over time "
    "(players who have been on Team A often are more likely to get Team B).\n\n"
    "Rating modes: use /ratemode to switch between:\n"
    "• 5skill — balances by 5 skill ratings\n"
    "• 2skill — balances by attacking + defending\n"
    "• performance — auto from goals/assists recorded via /record\n\n"
    "🔒 /record, /result, /setphoto and /removephoto are admin-only."
)


class SetPhotoFilter(filters.UpdateFilter):
    """Matches messages that start with /setphoto (text command or photo caption)."""

    def filter(self, update: Update) -> bool:
        message = update.effective_message
        if not message:
            return False
        text = message.text or message.caption or ""
        return text.startswith("/setphoto")


def _redraw_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Re-draw", callback_data=RE_DRAW_CALLBACK)]]
    )


def _tactic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Re-draw", callback_data=RE_DRAW_TACTIC_CALLBACK)]]
    )


def is_admin(update: Update) -> bool:
    """Check whether the sender is allowed to mutate data.

    Restricted to the user IDs in ADMIN_IDS (comma-separated in .env).
    If ADMIN_IDS is empty, everyone is allowed (backwards compatible).
    """
    admin_ids = os.getenv("ADMIN_IDS", "").strip()
    if not admin_ids:
        return True
    allowed = {int(x) for x in admin_ids.split(",") if x.strip().isdigit()}
    user_id = update.effective_user.id if update.effective_user else None
    return user_id in allowed


async def _guard_admin(update: Update) -> bool:
    """Reply a friendly message if the sender is not an admin. Returns True if allowed."""
    if is_admin(update):
        return True
    await update.effective_message.reply_text(
        "🔒 Sorry, only the group admin can use this command."
    )
    return False


async def _send_team_album(update: Update, team: dict[str, str], color: str) -> None:
    """Send an album of the team's player photos (skips players without photos)."""
    media = [
        InputMediaPhoto(media=path, caption=f"{color} {position} — {player}")
        for position in POSITION_ORDER
        for player in [team[position]]
        if (path := get_photo_path(player))
    ]
    if media:
        await update.message.reply_media_group(media)


async def _send_stats_album(
    update: Update, ranked: list, suffix: str
) -> None:
    """Send an album of player photos for a ranked stat list (best first)."""
    media = []
    for rank, (player, counts) in enumerate(ranked, start=1):
        path = get_photo_path(player)
        if path:
            count = counts["goals"] if suffix == "⚽" else counts["assists"]
            media.append(
                InputMediaPhoto(media=path, caption=f"{rank}. {player} — {count} {suffix}")
            )
    if media:
        await update.message.reply_media_group(media)


def _strength_and_prob_text(team_a: dict, team_b: dict) -> str:
    """Build the strength + win-probability lines when ratings are complete."""
    mode = get_rating_mode()
    strengths = build_strengths(
        mode,
        ratings_5=get_all_ratings(),
        ratings_2=get_all_ratings2(),
        stats=load_stats(),
    )
    if strengths is None:
        return (
            "\n_⚠️ Set all player ratings with /rate or /ratemode to see win probability._"
        )
    strength_a = team_strength(team_a, strengths)
    strength_b = team_strength(team_b, strengths)
    p_a, p_b = win_probability(team_a, team_b, strengths)
    mode_label = {"5skill": "5-Skill", "2skill": "2-Skill", "performance": "Performance"}
    return (
        "\n"
        f"💪 *Team Strength* — 🟩 {strength_a} vs 🟥 {strength_b}\n"
        f"📊 *Win Probability* — 🟩 {p_a}% | 🟥 {p_b}%\n"
        f"🏷 *Mode:* {mode_label.get(mode, mode)}"
    )



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN)


async def players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["*Player Pool*", ""]
    for position in POSITION_ORDER:
        p1, p2 = PLAYERS[position]
        lines.append(f"*{position}*: {p1} vs {p2}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        mode = get_rating_mode()
        strengths = build_strengths(
            mode,
            ratings_5=get_all_ratings(),
            ratings_2=get_all_ratings2(),
            stats=load_stats(),
        )
        team_a, team_b = generate_teams(team_a_counts(), strengths)
        record_draw(team_a, team_b)
        text = format_teams(team_a, team_b) + _strength_and_prob_text(team_a, team_b)
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_redraw_keyboard()
        )
        # Photo visualization: one album per team (skips players without photos).
        await _send_team_album(update, team_a, "🟩")
        await _send_team_album(update, team_b, "🟥")
    except Exception:
        logger.exception("Failed to generate teams for /draw")
        await update.message.reply_text(
            "😔 Something went wrong while drawing teams. Please try again."
        )


async def redraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-draw button: generate fresh teams and edit the existing message."""
    query = update.callback_query
    try:
        mode = get_rating_mode()
        strengths = build_strengths(
            mode,
            ratings_5=get_all_ratings(),
            ratings_2=get_all_ratings2(),
            stats=load_stats(),
        )
        team_a, team_b = generate_teams(team_a_counts(), strengths)
        record_draw(team_a, team_b)
        text = format_teams(team_a, team_b) + _strength_and_prob_text(team_a, team_b)
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_redraw_keyboard()
        )
    except Exception:
        logger.exception("Failed to re-draw teams via inline button")
        await query.answer("😔 Re-draw failed. Please try again.", show_alert=True)
        return
    await query.answer()


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show how balanced the draws have been (Team A vs Team B per player)."""
    try:
        draw_history = load_history()
        total = len(draw_history.get("draws", []))
        counts = draw_history.get("counts", {})
        lines = ["⚖️ *Draw Balance*", ""]
        if total == 0:
            lines.append("No draws recorded yet. Run /draw first.")
        else:
            for position in POSITION_ORDER:
                for player in PLAYERS[position]:
                    team_a_count = counts.get(player, 0)
                    team_b_count = total - team_a_count
                    lines.append(f"{player}: {team_a_count}A / {team_b_count}B")
            lines.append("")
            lines.append(f"Total draws: {total}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logger.exception("Failed to load draw history")
        await update.message.reply_text(
            "😔 Could not load the draw history. Please try again."
        )


async def _render_tactic() -> str:
    """Generate a fair draw and render both teams as a schematic pitch."""
    mode = get_rating_mode()
    strengths = build_strengths(
        mode,
        ratings_5=get_all_ratings(),
        ratings_2=get_all_ratings2(),
        stats=load_stats(),
    )
    team_a, team_b = generate_teams(team_a_counts(), strengths)
    record_draw(team_a, team_b)
    formation_name = get_formation()
    return (
        format_formation_team(team_a, formation_name, "Team A")
        + "\n\n"
        + format_formation_team(team_b, formation_name, "Team B")
        + _strength_and_prob_text(team_a, team_b)
    )


async def tactic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = await _render_tactic()
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_tactic_keyboard()
        )
    except Exception:
        logger.exception("Failed to render tactic")
        await update.message.reply_text(
            "😔 Could not render the tactic. Please try again."
        )


async def tactic_redraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        text = await _render_tactic()
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_tactic_keyboard()
        )
    except Exception:
        logger.exception("Failed to re-render tactic via inline button")
        await query.answer("😔 Re-draw failed. Please try again.", show_alert=True)
        return
    await query.answer()


async def formations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current = get_formation()
    customs = get_custom_formations()
    lines = ["🗂 *Formations*", "", f"Current: `{current}`", ""]
    for name in FORMATIONS:
        lines.append(f"• `{name}`")
    for name in customs:
        lines.append(f"• `{name}` 📦 (custom)")
    lines.append("")
    lines.append("Switch with `/formation <name>`.")
    lines.append("Add a custom one with `/formation add <name> D / M / A`.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


def _parse_custom_args(args: list[str]) -> tuple[str, list[str], list[str], list[str]]:
    """Parse /formation add <name> D / M / A into (name, defense, midfield, attack)."""
    if len(args) < 2 or args[0] != "add":
        raise ValueError(
            "Usage: `/formation add <name> D / M / A`\n\n"
            "Example:\n`/formation add 2-3-2 CB,RB / CM,RM,LM / FW,LB`"
        )
    groups: list[list[str]] = [[]]
    for token in args[2:]:
        if token == "/":
            groups.append([])
        else:
            groups[-1].extend(t.strip() for t in token.split(",") if t.strip())
    if len(groups) != 3:
        raise ValueError(
            "Usage: `/formation add <name> D / M / A`\n\n"
            "Example:\n`/formation add 2-3-2 CB,RB / CM,RM,LM / FW,LB`"
        )
    name = args[1]
    defense, midfield, attack = groups
    if not all((defense, midfield, attack)):
        raise ValueError("Each line (D, M, A) must have at least one position.")
    return name, defense, midfield, attack


async def formation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            f"Current formation: `{get_formation()}`.\n\n"
            "Set one with `/formation <name>` (e.g. `/formation 3-2-2`).\n"
            "Add a custom one with `/formation add <name> D / M / A`\n"
            "e.g. `/formation add 2-3-2 CB,RB / CM,RM,LM / FW,LB`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if args[0] == "add":
        try:
            name, defense, midfield, attack = _parse_custom_args(args)
            add_formation(name, defense, midfield, attack)
            set_formation(name)
        except ValueError as error:
            await update.message.reply_text(f"⚠️ {error}", parse_mode=ParseMode.MARKDOWN)
            return
        await update.message.reply_text(
            f"✅ Added custom formation `{name}` and activated it. Use /tactic to see it.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    name = args[0]
    try:
        set_formation(name)
    except ValueError as error:
        await update.message.reply_text(f"⚠️ {error}", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text(
        f"✅ Formation set to `{name}`. Use /tactic to see it on the pitch.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save a week's goals/assists, e.g. /record 3 Sahand:2:1,Hani:1:2."""
    if not await _guard_admin(update):
        return
    text = update.message.text or ""
    try:
        week, records = parse_record_input(text, ALL_PLAYER_NAMES)
    except ValueError as error:
        await update.message.reply_text(
            f"⚠️ {error}\n\n{RECORD_USAGE}", parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        set_week_record(week, records)
        goals = sum(goals for _, goals, _ in records)
        assists = sum(assists for _, _, assists in records)
        await update.message.reply_text(
            f"✅ *Week {week} saved*: {len(records)} players, "
            f"{goals} goals, {assists} assists.\n"
            "Use /stats for overall totals.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to save week %s record", week)
        await update.message.reply_text(
            "😔 Could not save the record. Please try again."
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        totals = aggregate_stats()
        await update.message.reply_text(
            format_overall_stats(totals), parse_mode=ParseMode.MARKDOWN
        )
        # Photo visualization of the top goalscorers and assissters.
        goals_list, assists_list = ranked_totals(totals)
        await _send_stats_album(update, goals_list, "⚽")
        await _send_stats_album(update, assists_list, "👟")
    except Exception:
        logger.exception("Failed to load overall stats")
        await update.message.reply_text(
            "😔 Could not load the statistics. Please try again."
        )


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/week <number>`\nExample: `/week 3`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        week_number = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "⚠️ The week must be a number, e.g. `/week 3`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        week_data = get_week_record(week_number)
        if week_data is None:
            await update.message.reply_text(f"No record found for *week {week_number}* yet.")
        else:
            await update.message.reply_text(
                format_week_stats(week_data, week_number),
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception:
        logger.exception("Failed to load week %s record", week_number)
        await update.message.reply_text(
            "😔 Could not load that week's statistics. Please try again."
        )


async def setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a player's photo. Send a photo with caption: /setphoto <player name>."""
    if not await _guard_admin(update):
        return
    message = update.effective_message
    text = message.text or message.caption or ""
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(
            "Send a photo with the caption:\n"
            "`/setphoto <player name>`\n\n"
            "Example: send a photo captioned `/setphoto Sahand`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    player = parts[1].strip()
    if player not in ALL_PLAYER_NAMES:
        await message.reply_text(
            f"⚠️ Unknown player '{player}'. Use /players to see exact names."
        )
        return
    if not message.photo:
        await message.reply_text(
            "⚠️ No photo attached. Send a photo with the caption "
            "`/setphoto <player name>`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        photo_file = await message.photo[-1].get_file()
        path = set_photo(player, photo_file.file_id)
        await photo_file.download_to_drive(path)
        logger.info("Saved photo for %s to %s", player, path)
        await message.reply_text(f"✅ Photo saved for *{player}*.", parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logger.exception("Failed to save photo for %s", player)
        await message.reply_text("😔 Could not save the photo. Please try again.")


async def removephoto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/removephoto <player name>`\nExample: `/removephoto Sahand`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    player = " ".join(args)
    if player not in ALL_PLAYER_NAMES:
        await update.message.reply_text(
            f"⚠️ Unknown player '{player}'. Use /players to see exact names."
        )
        return
    try:
        if remove_photo(player):
            await update.message.reply_text(
                f"🗑️ Photo removed for *{player}*.", parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(f"No photo on file for *{player}* yet.")
    except Exception:
        logger.exception("Failed to remove photo for %s", player)
        await update.message.reply_text("😔 Could not remove the photo. Please try again.")


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save a week's match score, e.g. /result 3 4:2 (uses the latest draw)."""
    if not await _guard_admin(update):
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            f"⚠️ Missing arguments.\n\n{RESULT_USAGE}", parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        week_number = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "⚠️ The week must be a number, e.g. `/result 3 4:2`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if week_number <= 0:
        await update.message.reply_text("⚠️ The week must be a positive number.")
        return

    score_text = args[1]
    try:
        score_a_text, score_b_text = score_text.split(":")
        score_a, score_b = int(score_a_text), int(score_b_text)
    except ValueError:
        await update.message.reply_text(
            f"⚠️ Bad score '{score_text}'. Use `scoreA:scoreB`, e.g. `4:2`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if score_a < 0 or score_b < 0:
        await update.message.reply_text("⚠️ Scores cannot be negative.")
        return

    draw = latest_draw()
    if draw is None:
        await update.message.reply_text(
            "⚠️ No recent draw found. Run /draw or /tactic first, then /result."
        )
        return

    try:
        set_result(
            week_number, score_a, score_b, draw["team_a"], draw["team_b"]
        )
        if score_a > score_b:
            verdict = "🟩 *Team A* won!"
        elif score_b > score_a:
            verdict = "🟥 *Team B* won!"
        else:
            verdict = "🤝 It's a draw!"
        await update.message.reply_text(
            f"✅ *Week {week_number} saved*: 🟩 Team A {score_a} : {score_b} 🟥 Team B\n"
            f"{verdict}\n"
            "Use /table to see updated win percentages.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to save result for week %s", week_number)
        await update.message.reply_text(
            "😔 Could not save the result. Please try again."
        )


async def table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(
            format_player_table(), parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        logger.exception("Failed to render player table")
        await update.message.reply_text(
            "😔 Could not load the player table. Please try again."
        )


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a player's five skill ratings: /rate <player> d p f pa de (1-10)."""
    try:
        if not await _guard_admin(update):
            return
        args = context.args or []
        if len(args) < 6:
            await update.message.reply_text(
                f"⚠️ Missing arguments.\n\n{RATE_USAGE}", parse_mode=ParseMode.MARKDOWN
            )
            return

        skills_raw = args[-5:]
        # Strip invisible Unicode chars (RTL marks, etc.) from the player name.
        player = " ".join(a.strip() for a in args[:-5])
        # Also strip invisible chars from skill values.
        skills_raw = [s.strip() for s in skills_raw]

        if player not in ALL_PLAYER_NAMES:
            await update.message.reply_text(
                f"⚠️ Unknown player '{player}'. Use /players to see exact names."
            )
            return

        values = {skill: int(value) for skill, value in zip(SKILLS, skills_raw)}
        set_player_skills(player, values)

        await update.message.reply_text(
            f"✅ Saved ratings for *{player}*.\nUse /rates to view all.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.exception("Failed to save rating")
        await update.message.reply_text(
            f"😔 Could not save the rating: {e}"
        )


async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(
            format_ratings_table(), parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        logger.exception("Failed to render ratings table")
        await update.message.reply_text(
            "😔 Could not load the ratings. Please try again."
        )


async def resetrates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_admin(update):
        return
    try:
        reset_ratings()
        await update.message.reply_text(
            "🗑️ All player ratings cleared. Use /rate to add them again."
        )
    except Exception:
        logger.exception("Failed to reset ratings")
        await update.message.reply_text(
            "😔 Could not reset the ratings. Please try again."
        )


async def rate2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a player's two skill ratings: /rate2 <player> attacking defending (1-10)."""
    try:
        if not await _guard_admin(update):
            return
        args = context.args or []
        if len(args) < 3:
            await update.message.reply_text(
                f"⚠️ Missing arguments.\n\n{RATE2_USAGE}", parse_mode=ParseMode.MARKDOWN
            )
            return

        skills_raw = args[-2:]
        player = " ".join(a.strip() for a in args[:-2])
        skills_raw = [s.strip() for s in skills_raw]

        if player not in ALL_PLAYER_NAMES:
            await update.message.reply_text(
                f"⚠️ Unknown player '{player}'. Use /players to see exact names."
            )
            return

        values = {skill: int(value) for skill, value in zip(SKILLS_2, skills_raw)}
        set_player_skills_2(player, values)

        await update.message.reply_text(
            f"✅ Saved 2-skill ratings for *{player}*.\nUse /rates2 to view all.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.exception("Failed to save 2-skill rating")
        await update.message.reply_text(
            f"😔 Could not save the rating: {e}"
        )


async def rates2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(
            format_ratings_table_2(), parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        logger.exception("Failed to render 2-skill ratings table")
        await update.message.reply_text(
            "😔 Could not load the ratings. Please try again."
        )


async def resetrates2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_admin(update):
        return
    try:
        reset_ratings2()
        await update.message.reply_text(
            "🗑️ All 2-skill ratings cleared. Use /rate2 to add them again."
        )
    except Exception:
        logger.exception("Failed to reset 2-skill ratings")
        await update.message.reply_text(
            "😔 Could not reset the ratings. Please try again."
        )


async def ratemode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show or set the current rating mode."""
    args = context.args or []
    valid_modes = ("5skill", "2skill", "performance")

    if not args:
        current = get_rating_mode()
        mode_label = {
            "5skill": "5-skill (/rate — Dribbling, Passing, Finishing, Pace, Defending)",
            "2skill": "2-skill (/rate2 — Attacking, Defending)",
            "performance": "Performance (auto from goals/assists via /record)",
        }
        await update.message.reply_text(
            f"🏷 *Current rating mode:* `{current}`\n\n{mode_label.get(current, '')}\n\n"
            "Switch with `/ratemode <mode>`:\n"
            "• `5skill` — manual 5-skill ratings\n"
            "• `2skill` — manual 2-skill ratings\n"
            "• `performance` — auto from game results",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    mode = args[0].strip().lower()
    if mode not in valid_modes:
        await update.message.reply_text(
            f"⚠️ Unknown mode '{mode}'. Choose from: {', '.join(valid_modes)}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        set_rating_mode(mode)
        mode_label = {
            "5skill": "5-skill (/rate)",
            "2skill": "2-skill (/rate2)",
            "performance": "Performance (auto from /record)",
        }
        await update.message.reply_text(
            f"✅ Rating mode set to *{mode}*.\n{mode_label.get(mode, '')}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.exception("Failed to set rating mode")
        await update.message.reply_text(
            f"😔 Could not set rating mode: {e}"
        )