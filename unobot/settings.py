from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CommandHandler, filters, MessageHandler, CallbackContext
from pony.orm import db_session

from utils import send_async
from user_setting import UserSetting
from locales import available_locales
from internationalization import _, user_locale


@user_locale
async def show_settings(update: Update, context: CallbackContext):
    chat = update.message.chat
    if update.message.chat.type != 'private':
        await send_async(context.bot, chat.id,
                         text=_("Please edit your settings in a private chat with the bot."))
        return
    with db_session:
        us = UserSetting.get(id=update.message.from_user.id)
        if not us:
            us = UserSetting(id=update.message.from_user.id)
        has_stats = us.stats
    if not has_stats:
        stats_btn = '📊 ' + _("Enable statistics")
    else:
        stats_btn = '❌ ' + _("Delete all statistics")
    kb = [[stats_btn], ['🌍 ' + _("Language")]]
    await send_async(context.bot, chat.id, text='🔧 ' + _("Settings"),
                     reply_markup=ReplyKeyboardMarkup(keyboard=kb, one_time_keyboard=True))


@user_locale
async def kb_select(update: Update, context: CallbackContext):
    chat = update.message.chat
    user = update.message.from_user
    option = context.matches[0].group(1)
    if option == '📊':
        with db_session:
            us = UserSetting.get(id=user.id)
            us.stats = True
        await send_async(context.bot, chat.id, text=_("Enabled statistics!"))
    elif option == '🌍':
        kb = [[locale + ' - ' + descr] for locale, descr in sorted(available_locales.items())]
        await send_async(context.bot, chat.id, text=_("Select locale"),
                         reply_markup=ReplyKeyboardMarkup(keyboard=kb, one_time_keyboard=True))
    elif option == '❌':
        with db_session:
            us = UserSetting.get(id=user.id)
            us.stats = False
            us.first_places = 0
            us.games_played = 0
            us.cards_played = 0
        await send_async(context.bot, chat.id, text=_("Deleted and disabled statistics!"))


@user_locale
async def locale_select(update: Update, context: CallbackContext):
    chat = update.message.chat
    user = update.message.from_user
    option = context.matches[0].group(1)
    if option in available_locales:
        with db_session:
            us = UserSetting.get(id=user.id)
            us.lang = option
        _.push(option)
        await send_async(context.bot, chat.id, text=_("Set locale!"))
        _.pop()


def register(app):
    app.add_handler(CommandHandler('settings', show_settings))
    app.add_handler(MessageHandler(
        filters.Regex('^([' + '📊' + '🌍' + '❌' + ']) .+$'),
        kb_select))
    app.add_handler(MessageHandler(
        filters.Regex(r'^(\w\w_\w\w) - .*'),
        locale_select))
