import gettext
import os
from functools import wraps

from locales import available_locales
from pony.orm import db_session
from user_setting import UserSetting
from shared_vars import gm

GETTEXT_DOMAIN = 'unobot'
GETTEXT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')


class _Underscore(object):
    def __init__(self):
        self.translators = {}
        for locale in available_locales.keys():
            if locale == 'en_US':
                continue
            path = gettext.find(GETTEXT_DOMAIN, GETTEXT_DIR, languages=[locale])
            if path:
                self.translators[locale] = gettext.GNUTranslations(open(path, 'rb'))
        self.locale_stack = list()

    def push(self, locale):
        self.locale_stack.append(locale)

    def pop(self):
        if self.locale_stack:
            return self.locale_stack.pop()
        return None

    @property
    def code(self):
        if self.locale_stack:
            return self.locale_stack[-1]
        return None

    def __call__(self, singular, plural=None, n=1, locale=None):
        if not locale:
            locale = self.locale_stack[-1]
        if locale not in self.translators.keys():
            return singular if n == 1 else plural
        translator = self.translators[locale]
        if plural is None:
            return translator.gettext(singular)
        return translator.ngettext(singular, plural, n)


_ = _Underscore()


def __(singular, plural=None, n=1, multi=False):
    translations = list()
    if not multi and len(set(_.locale_stack)) >= 1:
        translations.append(_(singular, plural, n, 'en_US'))
    else:
        for locale in _.locale_stack:
            translation = _(singular, plural, n, locale)
            if translation not in translations:
                translations.append(translation)
    return '\n'.join(translations)


def user_locale(func):
    @wraps(func)
    async def wrapped(update, context, *pargs, **kwargs):
        user = _user_chat_from_update(update)[0]
        with db_session:
            us = UserSetting.get(id=user.id)
            lang = us.lang if us and us.lang else 'en_US'
        if lang != 'en':
            _.push(lang)
        else:
            _.push('en_US')
        result = await func(update, context, *pargs, **kwargs)
        _.pop()
        return result
    return wrapped


def game_locales(func):
    @wraps(func)
    async def wrapped(update, context, *pargs, **kwargs):
        user, chat = _user_chat_from_update(update)
        locales = list()
        with db_session:
            player = gm.player_for_user_in_chat(user, chat)
            if player:
                for p in player.game.players:
                    us = UserSetting.get(id=p.user.id)
                    loc = us.lang if us and us.lang and us.lang != 'en' else 'en_US'
                    if loc not in locales:
                        _.push(loc)
                        locales.append(loc)
        result = await func(update, context, *pargs, **kwargs)
        while _.code:
            _.pop()
        return result
    return wrapped


def _user_chat_from_update(update):
    user = update.effective_user
    chat = update.effective_chat
    if chat is None and user is not None and user.id in gm.userid_current:
        chat = gm.userid_current.get(user.id).game.chat
    return user, chat
