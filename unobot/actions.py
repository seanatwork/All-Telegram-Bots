import logging
import card as c
from datetime import datetime

from telegram.ext import CallbackContext
from apscheduler.jobstores.base import JobLookupError
from pony.orm import db_session

from config import TIME_REMOVAL_AFTER_SKIP, MIN_FAST_TURN_TIME
from errors import DeckEmptyError, NotEnoughPlayersError
from internationalization import __, _
from shared_vars import gm
from user_setting import UserSetting
from utils import send_async, display_name, game_is_running

logger = logging.getLogger(__name__)


class Countdown(object):
    def __init__(self, player, job_queue):
        self.player = player
        self.job_queue = job_queue


async def do_skip(bot, player, job_queue=None):
    game = player.game
    chat = game.chat
    skipped_player = game.current_player
    next_player = game.current_player.next

    if skipped_player.waiting_time > 0:
        skipped_player.anti_cheat += 1
        skipped_player.waiting_time -= TIME_REMOVAL_AFTER_SKIP
        if skipped_player.waiting_time < 0:
            skipped_player.waiting_time = 0
        try:
            skipped_player.draw()
        except DeckEmptyError:
            pass
        n = skipped_player.waiting_time
        await send_async(bot, chat.id,
                         text=__("Waiting time to skip this player has "
                                 "been reduced to {time} seconds.\n"
                                 "Next player: {name}", multi=game.translate)
                         .format(time=n, name=display_name(next_player.user)))
        logger.info("{player} was skipped!".format(player=display_name(player.user)))
        game.turn()
        if job_queue:
            start_player_countdown(bot, game, job_queue)
    else:
        try:
            gm.leave_game(skipped_player.user, chat)
            await send_async(bot, chat.id,
                             text=__("{name1} ran out of time "
                                     "and has been removed from the game!\n"
                                     "Next player: {name2}", multi=game.translate)
                             .format(name1=display_name(skipped_player.user),
                                     name2=display_name(next_player.user)))
            logger.info("{player} was skipped!".format(player=display_name(player.user)))
            if job_queue:
                start_player_countdown(bot, game, job_queue)
        except NotEnoughPlayersError:
            await send_async(bot, chat.id,
                             text=__("{name} ran out of time "
                                     "and has been removed from the game!\n"
                                     "The game ended.", multi=game.translate)
                             .format(name=display_name(skipped_player.user)))
            gm.end_game(chat, skipped_player.user)


async def do_play_card(bot, player, result_id):
    card = c.from_str(result_id)
    player.play(card)
    game = player.game
    chat = game.chat
    user = player.user

    with db_session:
        us = UserSetting.get(id=user.id)
        if not us:
            us = UserSetting(id=user.id)
        if us.stats:
            us.cards_played += 1
        choosing_color = game.choosing_color
        cards_left = len(player.cards)
        if cards_left == 0:
            if us.stats:
                us.games_played += 1
                if game.players_won == 0:
                    us.first_places += 1
            game.players_won += 1

    if choosing_color:
        await send_async(bot, chat.id, text=__("Please choose a color", multi=game.translate))
    if cards_left == 1:
        await send_async(bot, chat.id, text="UNO!")
    if cards_left == 0:
        await send_async(bot, chat.id,
                         text=__("{name} won!", multi=game.translate)
                         .format(name=user.first_name))
        try:
            gm.leave_game(user, chat)
        except NotEnoughPlayersError:
            await send_async(bot, chat.id, text=__("Game ended!", multi=game.translate))
            with db_session:
                us2 = UserSetting.get(id=game.current_player.user.id)
                if us2 and us2.stats:
                    us2.games_played += 1
            gm.end_game(chat, user)


async def do_draw(bot, player):
    game = player.game
    draw_counter_before = game.draw_counter
    try:
        player.draw()
    except DeckEmptyError:
        await send_async(bot, player.game.chat.id,
                         text=__("There are no more cards in the deck.", multi=game.translate))
    if (game.last_card.value == c.DRAW_TWO or
            game.last_card.special == c.DRAW_FOUR) and draw_counter_before > 0:
        game.turn()


async def do_call_bluff(bot, player):
    game = player.game
    chat = game.chat
    if player.prev.bluffing:
        await send_async(bot, chat.id,
                         text=__("Bluff called! Giving 4 cards to {name}", multi=game.translate)
                         .format(name=player.prev.user.first_name))
        try:
            player.prev.draw()
        except DeckEmptyError:
            await send_async(bot, player.game.chat.id,
                             text=__("There are no more cards in the deck.", multi=game.translate))
    else:
        game.draw_counter += 2
        await send_async(bot, chat.id,
                         text=__("{name1} didn't bluff! Giving 6 cards to {name2}", multi=game.translate)
                         .format(name1=player.prev.user.first_name, name2=player.user.first_name))
        try:
            player.draw()
        except DeckEmptyError:
            await send_async(bot, player.game.chat.id,
                             text=__("There are no more cards in the deck.", multi=game.translate))
    game.turn()


def start_player_countdown(bot, game, job_queue):
    player = game.current_player
    time = player.waiting_time
    if time < MIN_FAST_TURN_TIME:
        time = MIN_FAST_TURN_TIME
    if game.mode == 'fast':
        if game.job:
            try:
                game.job.schedule_removal()
            except JobLookupError:
                pass
        job = job_queue.run_once(skip_job, time, data=Countdown(player, job_queue))
        logger.info("Started countdown for player: {player}. {time} seconds."
                    .format(player=display_name(player.user), time=time))
        player.game.job = job


async def skip_job(context: CallbackContext):
    player = context.job.data.player
    game = player.game
    if game_is_running(game):
        job_queue = context.job.data.job_queue
        await do_skip(context.bot, player, job_queue)
