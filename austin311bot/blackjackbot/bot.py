# -*- coding: utf-8 -*-

import logging
import logging.handlers
import pathlib

from telegram.ext import ApplicationBuilder

import config
from blackjackbot import handlers, error_handler
from blackjackbot.gamestore import GameStore

# Log to stdout for Fly.io/main.py consistency
logger = logging.getLogger(__name__)

async def stale_game_cleaner(context):
    gs = GameStore()
    gs.cleanup_stale_games()

def build_app():
    # Load configuration
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    for handler in handlers:
        application.add_handler(handler)

    application.add_error_handler(error_handler)

    # Set up jobs
    application.job_queue.run_repeating(callback=stale_game_cleaner, interval=300, first=300)
    
    return application

if __name__ == '__main__':
    # Standard standalone run
    logging.basicConfig(level=logging.INFO)
    application = build_app()
    application.run_polling()
