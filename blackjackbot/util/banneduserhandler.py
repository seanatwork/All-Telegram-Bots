# -*- coding: utf-8 -*-
import logging

from telegram.ext import TypeHandler

import database


class BannedUserHandler(TypeHandler):
    logger = logging.getLogger(__name__)

    def check_update(self, update):
        if not isinstance(update, self.type):
            return None

        db = database.Database()
        user = update.effective_user

        if user is None:
            return None

        if db.is_user_banned(user.id):
            return update

        return None
