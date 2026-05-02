from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackContext
from pony.orm import db_session

from user_setting import UserSetting
from utils import send_async
from internationalization import _, user_locale
from promotions import send_promotion


@user_locale
async def help_handler(update: Update, context: CallbackContext):
    help_text = _("Follow these steps:\n\n"
                  "1. Add this bot to a group\n"
                  "2. In the group, start a new game with /new or join an already"
                  " running game with /join\n"
                  "3. After at least two players have joined, start the game with"
                  " /start\n"
                  "4. Type <code>@unobot</code> into your chat box and hit "
                  "<b>space</b>, or click the <code>via @unobot</code> text "
                  "next to messages. You will see your cards (some greyed out), "
                  "any extra options like drawing, and a <b>?</b> to see the "
                  "current game state. The <b>greyed out cards</b> are those you "
                  "<b>can not play</b> at the moment. Tap an option to execute "
                  "the selected action.\n"
                  "Players can join the game at any time. To leave a game, "
                  "use /leave. If a player takes more than 90 seconds to play, "
                  "you can use /skip to skip that player. Use /notify_me to "
                  "receive a private message when a new game is started.\n\n"
                  "<b>Language</b> and other settings: /settings\n"
                  "Other commands (only game creator):\n"
                  "/close - Close lobby\n"
                  "/open - Open lobby\n"
                  "/kill - Terminate the game\n"
                  "/kick - Select a player to kick "
                  "by replying to him or her\n"
                  "/enable_translations - Translate relevant texts into all "
                  "languages spoken in a game\n"
                  "/disable_translations - Use English for those texts\n\n"
                  "<b>Experimental:</b> Play in multiple groups at the same time. "
                  "Press the <code>Current game: ...</code> button and select the "
                  "group you want to play a card in.\n"
                  "If you enjoy this bot, "
                  "<a href=\"https://telegram.me/storebot?start=mau_mau_bot\">"
                  "rate me</a>, join the "
                  "<a href=\"https://telegram.me/unobotnews\">update channel</a>"
                  " and buy an UNO card game.")
    await update.message.chat.send_message(help_text, parse_mode=ParseMode.HTML,
                                           disable_web_page_preview=True)
    await send_promotion(update.effective_chat)


@user_locale
async def modes(update: Update, context: CallbackContext):
    modes_explanation = _("This UNO bot has four game modes: Classic, Sanic, Wild and Text.\n\n"
                          " 🎻 The Classic mode uses the conventional UNO deck and there is no auto skip.\n"
                          " 🚀 The Sanic mode uses the conventional UNO deck and the bot automatically skips a player if he/she takes too long to play its turn\n"
                          " 🐉 The Wild mode uses a deck with more special cards, less number variety and no auto skip.\n"
                          " ✍️ The Text mode uses the conventional UNO deck but instead of stickers it uses the text.\n\n"
                          "To change the game mode, the GAME CREATOR has to type the bot nickname and a space, "
                          "just like when playing a card, and all gamemode options should appear.")
    await send_async(context.bot, update.message.chat_id, text=modes_explanation,
                     parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@user_locale
async def source(update: Update, context: CallbackContext):
    source_text = _("This bot is Free Software and licensed under the AGPL. "
                    "The code is available here: \n"
                    "https://github.com/jh0ker/mau_mau_bot")
    attributions = _("Attributions:\n"
                     'Draw icon by <a href="http://www.faithtoken.com/">Faithtoken</a>\n'
                     'Pass icon by <a href="http://delapouite.com/">Delapouite</a>\n'
                     "Originals available on http://game-icons.net\n"
                     "Icons edited by ɳick")
    await send_async(context.bot, update.message.chat_id,
                     text=source_text + '\n' + attributions,
                     parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@user_locale
async def news(update: Update, context: CallbackContext):
    await send_async(context.bot, update.message.chat_id,
                     text=_("All news here: https://telegram.me/unobotnews"),
                     disable_web_page_preview=True)


@user_locale
async def stats(update: Update, context: CallbackContext):
    user = update.message.from_user
    with db_session:
        us = UserSetting.get(id=user.id)
        if not us or not us.stats:
            await send_async(context.bot, update.message.chat_id,
                             text=_("You did not enable statistics. Use /settings in "
                                    "a private chat with the bot to enable them."))
            return
        stats_text = [
            _("{number} game played", "{number} games played", us.games_played)
            .format(number=us.games_played),
            _("{number} first place ({percent}%)", "{number} first places ({percent}%)", us.first_places)
            .format(number=us.first_places,
                    percent=round((us.first_places / us.games_played) * 100) if us.games_played else 0),
            _("{number} card played", "{number} cards played", us.cards_played)
            .format(number=us.cards_played),
        ]
    await send_async(context.bot, update.message.chat_id, text='\n'.join(stats_text))


def register(app):
    app.add_handler(CommandHandler('help', help_handler))
    app.add_handler(CommandHandler('source', source))
    app.add_handler(CommandHandler('news', news))
    app.add_handler(CommandHandler('stats', stats))
    app.add_handler(CommandHandler('modes', modes))
