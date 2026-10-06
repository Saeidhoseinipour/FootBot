"""Entry point: loads the bot token, wires up handlers and starts polling."""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
)
from telegram.request import HTTPXRequest

from handlers import (
    RE_DRAW_CALLBACK,
    RE_DRAW_TACTIC_CALLBACK,
    SetPhotoFilter,
    draw,
    formation,
    formations,
    history,
    players,
    rate,
    rate2,
    ratemode,
    rates,
    rates2,
    record,
    redraw_callback,
    removephoto,
    resetrates,
    resetrates2,
    result,
    setphoto,
    start,
    stats,
    table,
    tactic,
    tactic_redraw_callback,
    week,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error(
            "BOT_TOKEN not set. Copy .env.example to .env and fill in your token."
        )
        return

    # The default 5s timeouts are too tight for slow/restricted networks
    # (e.g. Telegram behind a VPN/filter). Use generous timeouts instead.
    request_kwargs: dict = {
        "connect_timeout": 30.0,
        "read_timeout": 30.0,
        "write_timeout": 30.0,
        "pool_timeout": 30.0,
    }
    # Optional: route through a proxy (e.g. a local SOCKS/HTTP proxy) if the
    # Telegram API is blocked on your network. Set PROXY in your .env file.
    proxy = os.getenv("PROXY")
    if proxy:
        request_kwargs["proxy"] = proxy
        logger.info("Using proxy: %s", proxy)
    request = HTTPXRequest(**request_kwargs)
    application = ApplicationBuilder().token(token).request(request).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("players", players))
    application.add_handler(CommandHandler("draw", draw))
    application.add_handler(CommandHandler("record", record))
    application.add_handler(CommandHandler("rate", rate))
    application.add_handler(CommandHandler("rates", rates))
    application.add_handler(CommandHandler("resetrates", resetrates))
    application.add_handler(CommandHandler("rate2", rate2))
    application.add_handler(CommandHandler("rates2", rates2))
    application.add_handler(CommandHandler("resetrates2", resetrates2))
    application.add_handler(CommandHandler("ratemode", ratemode))
    application.add_handler(CommandHandler("result", result))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("table", table))
    application.add_handler(CommandHandler("week", week))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("tactic", tactic))
    application.add_handler(CommandHandler("formation", formation))
    application.add_handler(CommandHandler("formations", formations))
    application.add_handler(MessageHandler(SetPhotoFilter(), setphoto))
    application.add_handler(CommandHandler("removephoto", removephoto))
    application.add_handler(CallbackQueryHandler(redraw_callback, pattern=RE_DRAW_CALLBACK))
    application.add_handler(
        CallbackQueryHandler(tactic_redraw_callback, pattern=RE_DRAW_TACTIC_CALLBACK)
    )

    logger.info("Bot started, polling for updates...")
    application.run_polling()


if __name__ == "__main__":
    main()