# -*- coding: utf-8 -*-

import logging
import pathlib

from telegram.ext import ApplicationBuilder

from blackjackbot.blackjack_config import BOT_TOKEN, USE_WEBHOOK, WEBHOOK_IP, WEBHOOK_PORT, WEBHOOK_URL
from blackjackbot import handlers, error_handler
from blackjackbot.gamestore import GameStore

# Use standard logger consistent with main.py
logger = logging.getLogger(__name__)

async def stale_game_cleaner(context):
    gs = GameStore()
    gs.cleanup_stale_games()

def build_app():
    """Build and return the Telegram application instance."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    for handler in handlers:
        application.add_handler(handler)

    application.add_error_handler(error_handler)

    # Set up jobs
    application.job_queue.run_repeating(callback=stale_game_cleaner, interval=300, first=300)
    
    return application

if __name__ == '__main__':
    # Standard standalone run for development
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    application = build_app()
    
    if USE_WEBHOOK:
        logger.info("Starting webhook...")
        application.run_webhook(
            listen=WEBHOOK_IP,
            port=WEBHOOK_PORT,
            url_path=BOT_TOKEN,
            webhook_url=WEBHOOK_URL
        )
    else:
        logger.info("Starting polling...")
        application.run_polling()
