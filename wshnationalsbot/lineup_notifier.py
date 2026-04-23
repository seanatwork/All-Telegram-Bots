"""Lineup notification system for Washington Nationals games."""
import asyncio
import json
import os
import threading
import requests
import pytz
from datetime import date, datetime

from logger import get_logger
from wshnats_config import NATIONALS_TEAM_ID, TIMEZONE, SUBSCRIBERS_FILE, LINEUP_CHANNEL_ID

logger = get_logger(__name__)

_file_lock = threading.RLock()

_lineup_sent: set[int] = set()
_channel_lineup_sent: set[int] = set()

_LINEUP_STATE_FILE = os.path.join(os.path.dirname(SUBSCRIBERS_FILE) or ".", "lineup_state.json")


def _load_lineup_state() -> None:
    global _lineup_sent, _channel_lineup_sent
    try:
        if os.path.exists(_LINEUP_STATE_FILE):
            with open(_LINEUP_STATE_FILE) as f:
                data = json.load(f)
            _lineup_sent = set(data.get("lineup_sent", []))
            _channel_lineup_sent = set(data.get("channel_lineup_sent", []))
            logger.info(f"Loaded lineup state ({len(_lineup_sent)} sent, {len(_channel_lineup_sent)} channel)")
    except Exception as e:
        logger.warning(f"Failed to load lineup state: {e}")


def _save_lineup_state() -> None:
    try:
        os.makedirs(os.path.dirname(_LINEUP_STATE_FILE) or ".", exist_ok=True)
        tmp = _LINEUP_STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump({
                "lineup_sent": list(_lineup_sent),
                "channel_lineup_sent": list(_channel_lineup_sent),
            }, f)
        os.replace(tmp, _LINEUP_STATE_FILE)
    except Exception as e:
        logger.warning(f"Failed to save lineup state: {e}")


_load_lineup_state()


# ---------------------------------------------------------------------------
# Subscriber management
# ---------------------------------------------------------------------------

def load_subscribers() -> set[int]:
    with _file_lock:
        if not os.path.exists(SUBSCRIBERS_FILE):
            return set()
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                data = json.load(f)
            return set(data.get("subscribers", []))
        except Exception as e:
            logger.error(f"Error loading subscribers: {e}")
            return set()


def _save_subscribers(subscribers: set[int]) -> None:
    """Write subscriber set to disk. Must be called with _file_lock held."""
    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE) or ".", exist_ok=True)
    tmp = SUBSCRIBERS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"subscribers": list(subscribers)}, f)
    os.replace(tmp, SUBSCRIBERS_FILE)  # atomic on POSIX


def add_subscriber(chat_id: int) -> bool:
    """Add a subscriber. Returns True if newly added, False if already subscribed."""
    with _file_lock:
        subs = load_subscribers()
        if chat_id in subs:
            return False
        subs.add(chat_id)
        _save_subscribers(subs)
    return True


def remove_subscriber(chat_id: int) -> bool:
    """Remove a subscriber. Returns True if removed, False if wasn't subscribed."""
    with _file_lock:
        subs = load_subscribers()
        if chat_id not in subs:
            return False
        subs.discard(chat_id)
        _save_subscribers(subs)
    return True


# ---------------------------------------------------------------------------
# MLB API — lineup fetching
# ---------------------------------------------------------------------------

def _fetch_todays_game() -> dict | None:
    """Return today's Nationals game dict (with lineups hydrated), or None."""
    today = date.today().strftime("%Y-%m-%d")
    resp = requests.get(
        "https://statsapi.mlb.com/api/v1/schedule",
        params={
            "teamId": NATIONALS_TEAM_ID,
            "startDate": today,
            "endDate": today,
            "sportId": 1,
            "hydrate": "lineups",
        },
        timeout=15,
    )
    resp.raise_for_status()
    for date_entry in resp.json().get("dates", []):
        for game in date_entry.get("games", []):
            return game
    return None


def _format_lineup(game: dict) -> str | None:
    """Format lineup message. Returns None if lineup not yet posted."""
    lineups = game.get("lineups", {})
    home_players = lineups.get("homePlayers", [])
    away_players = lineups.get("awayPlayers", [])

    # Wait until BOTH teams have lineups before posting
    if not home_players or not away_players:
        return None

    teams = game.get("teams", {})
    home_name = teams.get("home", {}).get("team", {}).get("name", "Home")
    away_name = teams.get("away", {}).get("team", {}).get("name", "Away")

    game_dt_str = game.get("gameDate", "")
    try:
        game_dt = datetime.strptime(game_dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        local_dt = game_dt.astimezone(pytz.timezone(TIMEZONE))
        hour = local_dt.hour % 12 or 12
        minute = local_dt.strftime("%M")
        am_pm = local_dt.strftime("%p")
        tz_abbr = local_dt.tzname() or "ET"
        time_str = f"{hour}:{minute} {am_pm} {tz_abbr}"
    except Exception:
        time_str = ""

    lines = [f"<b>⚾ Today's Lineup</b>", f"<b>{away_name} @ {home_name}</b>"]
    if time_str:
        lines.append(f"<i>{time_str}</i>")

    def fmt_players(players: list, team_name: str) -> None:
        if not players:
            return
        is_nats = team_name == "Washington Nationals"
        lines.append(f"\n<b>{team_name}{'  🌹' if is_nats else ''}</b>")
        for i, p in enumerate(players, 1):
            name = p.get("fullName") or p.get("lastName", "Unknown")
            pos = p.get("primaryPosition", {}).get("abbreviation", "")
            pos_str = f" · {pos}" if pos else ""
            lines.append(f"{i}. {name}{pos_str}")

    fmt_players(away_players, away_name)
    fmt_players(home_players, home_name)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Polling job
# ---------------------------------------------------------------------------

async def check_and_notify(context) -> None:
    """Job that runs every 10 min: notify subscribers when lineup is posted."""
    try:
        game = await asyncio.to_thread(_fetch_todays_game)
        if game is None:
            return

        game_pk = game.get("gamePk")
        if game_pk in _lineup_sent and game_pk in _channel_lineup_sent:
            return  # Already fully processed for this game

        # Only poll within the 3-hour window before first pitch
        game_dt_str = game.get("gameDate", "")
        try:
            game_dt = datetime.strptime(game_dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
            now_utc = datetime.now(pytz.utc)
            hours_until = (game_dt - now_utc).total_seconds() / 3600
            if hours_until > 3 or hours_until < -1:
                return
        except Exception:
            pass

        message = _format_lineup(game)
        if message is None:
            return

        # Post to channel
        if LINEUP_CHANNEL_ID and game_pk not in _channel_lineup_sent:
            try:
                await context.bot.send_message(
                    chat_id=LINEUP_CHANNEL_ID,
                    text=message,
                    parse_mode="HTML",
                )
                logger.info(f"Lineup posted to channel {LINEUP_CHANNEL_ID} for gamePk {game_pk}")
            except Exception as e:
                # Always mark as handled (even on error) to prevent re-posting if Telegram
                # received the message but the response didn't make it back to us.
                logger.warning(f"Failed to post lineup to channel: {e}")
            finally:
                _channel_lineup_sent.add(game_pk)
                _save_lineup_state()

        # DM subscribers
        subscribers = load_subscribers()
        if not subscribers:
            logger.info("Lineup available but no subscribers to notify.")
        else:
            for chat_id in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"Failed to send lineup to {chat_id}: {e}")
            logger.info(f"Lineup sent to {len(subscribers)} subscriber(s) for gamePk {game_pk}")

        _lineup_sent.add(game_pk)
        _save_lineup_state()

    except Exception as e:
        logger.error(f"Error in lineup check_and_notify: {e}")
