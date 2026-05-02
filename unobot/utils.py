import logging
from telegram import Update
from telegram.ext import CallbackContext

from internationalization import _, __
from shared_vars import gm

logger = logging.getLogger(__name__)

TIMEOUT = 2.5


def list_subtract(list1, list2):
    list1 = list1.copy()
    for x in list2:
        list1.remove(x)
    return list(sorted(list1))


def display_name(user):
    user_name = user.first_name
    if user.username:
        user_name += ' (@' + user.username + ')'
    return user_name


def display_color(color):
    if color == "r":
        return _("{emoji} Red").format(emoji='❤️')
    if color == "b":
        return _("{emoji} Blue").format(emoji='💙')
    if color == "g":
        return _("{emoji} Green").format(emoji='💚')
    if color == "y":
        return _("{emoji} Yellow").format(emoji='💛')


def display_color_group(color, game):
    if color == "r":
        return __("{emoji} Red", game.translate).format(emoji='❤️')
    if color == "b":
        return __("{emoji} Blue", game.translate).format(emoji='💙')
    if color == "g":
        return __("{emoji} Green", game.translate).format(emoji='💚')
    if color == "y":
        return __("{emoji} Yellow", game.translate).format(emoji='💛')


async def error(update: Update, context: CallbackContext):
    logger.exception(context.error)


async def send_async(bot, *args, **kwargs):
    kwargs.pop('timeout', None)
    try:
        await bot.send_message(*args, **kwargs)
    except Exception:
        logger.exception("Error sending message")


async def answer_async(bot, *args, **kwargs):
    kwargs.pop('timeout', None)
    try:
        await bot.answer_inline_query(*args, **kwargs)
    except Exception:
        logger.exception("Error answering inline query")


def game_is_running(game):
    return game in gm.chatid_games.get(game.chat.id, list())


def user_is_creator(user, game):
    return user.id in game.owner


async def user_is_admin(user, bot, chat):
    return user.id in await get_admin_ids(bot, chat.id)


async def user_is_creator_or_admin(user, game, bot, chat):
    return user_is_creator(user, game) or await user_is_admin(user, bot, chat)


async def get_admin_ids(bot, chat_id):
    return [admin.user.id for admin in await bot.get_chat_administrators(chat_id)]
