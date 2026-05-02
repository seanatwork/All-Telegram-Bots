import json
import logging
import os
from html import escape as escape_html

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle,
    InputTextMessageContent, Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CallbackContext, CallbackQueryHandler, CommandHandler,
    InlineQueryHandler,
)

import emojis
from data import get_game, reset_game

logger = logging.getLogger(__name__)


def mention(name: str, user_id: int) -> str:
    return f'<a href="tg://user?id={user_id}">{escape_html(name)}</a>'


def player_callback_data(user_id: int, name: str) -> str:
    """Build a P-type callback payload that fits in Telegram's 64-byte cap."""
    for trim in (24, 16, 8, 0):
        candidate_name = name[:trim] if trim else "Player"
        payload = json.dumps({"type": "P", "id": user_id, "name": candidate_name})
        if len(payload.encode("utf-8")) <= 64:
            return payload
    return json.dumps({"type": "P", "id": user_id, "name": "P"})


def header(game) -> str:
    return (
        f"{mention(game.player1['name'], game.player1['id'])}({emojis.X})  "
        f"{emojis.vs}  "
        f"{mention(game.player2['name'], game.player2['id'])}({emojis.O})"
    )


def turn_status(game) -> str:
    next_player = game.player1 if game.whose_turn else game.player2
    next_emoji = emojis.X if game.whose_turn else emojis.O
    return f"{emojis.game} <b>{mention(next_player['name'], next_player['id'])} ({next_emoji})</b>"


async def start(update: Update, context: CallbackContext):
    if not update.message or not update.message.from_user:
        return
    bot_username = context.bot.username or "this bot"
    text = (
        f"Hi <b>{escape_html(update.message.from_user.first_name)}</b>\n\n"
        f"To begin, start a message with @{bot_username} in any chat you want, "
        f"or tap <b>Play</b> and pick a chat."
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            emojis.game + " Play",
            switch_inline_query=emojis.game,
        )]]),
    )


async def contact(update: Update, context: CallbackContext):
    if not update.message:
        return
    await update.message.reply_text(
        "Feedback or issues? Reach out to @seansullivan.",
        parse_mode=ParseMode.HTML,
    )


async def inline_handler(update: Update, context: CallbackContext):
    query = update.inline_query
    if not query or not query.from_user:
        return
    accept_button = InlineKeyboardButton(
        emojis.swords + " Accept",
        callback_data=player_callback_data(query.from_user.id, query.from_user.first_name),
    )
    result = InlineQueryResultArticle(
        id="xo",
        title="Tic-Tac-Toe",
        input_message_content=InputTextMessageContent(
            f"<b>{escape_html(query.from_user.first_name)}</b> challenged you in XO!",
            parse_mode=ParseMode.HTML,
        ),
        description="Tap here to challenge your friends in XO!",
        thumbnail_url=(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/"
            "Tic_tac_toe.svg/1200px-Tic_tac_toe.svg.png"
        ),
        reply_markup=InlineKeyboardMarkup([[accept_button]]),
    )
    await query.answer(results=[result], cache_time=1)


async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query or not query.data:
        return

    try:
        data = json.loads(query.data)
    except (json.JSONDecodeError, TypeError):
        await query.answer()
        return

    if not query.inline_message_id:
        await query.answer()
        return

    game = get_game(query.inline_message_id, data)
    if game is None:
        await query.answer("Game expired — start a new one!", show_alert=True)
        return

    kind = data.get("type")
    if kind == "P":
        await _handle_join(update, context, game)
    elif kind == "K":
        await _handle_move(update, context, game, data)
    elif kind == "R":
        await _handle_reset(update, context, game)
    else:
        await query.answer()


async def _handle_join(update, context, game):
    query = update.callback_query
    if game.player1["id"] == query.from_user.id:
        await query.answer("Wait for opponent!", show_alert=True)
        return

    game.player2 = {
        "id": query.from_user.id,
        "name": query.from_user.first_name,
    }
    text = f"{header(game)}\n\n{turn_status(game)}"
    await query.answer()
    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(game.board_keys),
    )


async def _handle_move(update, context, game, data):
    query = update.callback_query
    if data.get("end"):
        await query.answer("Match has ended!", show_alert=True)
        return
    if game.player2 is None:
        await query.answer("Waiting for an opponent.", show_alert=True)
        return

    is_p1_turn = game.whose_turn
    if (is_p1_turn and query.from_user.id != game.player1["id"]) \
            or (not is_p1_turn and query.from_user.id != game.player2["id"]):
        await query.answer("Not your turn!")
        return

    if not game.fill_board(query.from_user.id, data["coord"]):
        await query.answer("That cell's already taken.")
        return

    game.whose_turn = not game.whose_turn

    if game.check_winner():
        status = (
            f"{emojis.trophy} <b>{mention(game.winner['name'], game.winner['id'])} won!</b>"
        )
    elif game.is_draw():
        status = f"{emojis.draw} <b>Draw!</b>"
    else:
        status = turn_status(game)

    await query.answer()
    await query.edit_message_text(
        text=f"{header(game)}\n\n{status}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(game.board_keys),
    )


async def _handle_reset(update, context, game):
    query = update.callback_query
    if game.player2 is None:
        await query.answer("Game expired — start a new one!", show_alert=True)
        return
    new_game = reset_game(game)
    if new_game is None:
        await query.answer("Game expired — start a new one!", show_alert=True)
        return
    await query.answer()
    await query.edit_message_text(
        text=f"{header(new_game)}\n\n{turn_status(new_game)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(new_game.board_keys),
    )


def build_app():
    token = os.environ["XO_BOT_TOKEN"]
    app = (ApplicationBuilder()
           .token(token)
           .connect_timeout(30)
           .read_timeout(30)
           .build())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("contact", contact))
    app.add_handler(InlineQueryHandler(inline_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app
