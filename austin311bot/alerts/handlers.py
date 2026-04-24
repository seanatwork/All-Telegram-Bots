"""Telegram handlers for alert subscription management.

Uses context.user_data for state instead of ConversationHandler to avoid
PTB 21 per_message conflicts with mixed inline/text flows.

Commands:
  /subscribe   — start subscription flow
  /myalerts    — list active subscriptions
  /unsubscribe — cancel all alerts
  /deletedata  — wipe all stored data
"""

import asyncio
import logging
import os

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from alerts import db

logger = logging.getLogger(__name__)

# user_data keys
_STATE     = "alert_state"
_TYPE      = "alert_type"

# States
_AWAITING_ADDRESS = "awaiting_address"

ALERT_TYPES = {
    "crime_daily":     "🚨 Daily Crime Report",
    "district_digest": "📊 Weekly District Digest",
}

DISTRICT_LABELS = {
    "1":  "District 1 (NE Austin)",
    "2":  "District 2 (SE Austin)",
    "3":  "District 3 (E Austin / Cesar Chavez)",
    "4":  "District 4 (S Austin / Oltorf)",
    "5":  "District 5 (S Austin / Slaughter)",
    "6":  "District 6 (NW / Jollyville)",
    "7":  "District 7 (N Central / Crestview)",
    "8":  "District 8 (SW / Oak Hill)",
    "9":  "District 9 (Central / Downtown)",
    "10": "District 10 (W Austin / Westlake Hills)",
}


# ── geocoding ──────────────────────────────────────────────────────────────────

def _geocode_to_district(address: str) -> str | None:
    """Geocode an address string → Austin council district number, or None."""
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not maps_key:
        return None

    try:
        geo = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": f"{address}, Austin TX", "key": maps_key},
            timeout=10,
        ).json()
        if geo.get("status") != "OK":
            return None
        loc = geo["results"][0]["geometry"]["location"]
        lat, lon = loc["lat"], loc["lng"]
    except Exception as e:
        logger.error(f"geocode: {e}")
        return None

    try:
        arcgis = requests.get(
            "https://services.arcgis.com/0L95CJ0VTaxqcmED/ArcGIS/rest/services"
            "/Council_Districts/FeatureServer/0/query",
            params={
                "geometry":     f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR":         "4326",
                "spatialRel":   "esriSpatialRelIntersects",
                "outFields":    "COUNCIL_DI",
                "f":            "json",
            },
            timeout=10,
        ).json()
        features = arcgis.get("features", [])
        if not features:
            logger.warning(f"ArcGIS returned no district for {lat},{lon}")
            return None
        return str(features[0]["attributes"]["COUNCIL_DI"])
    except Exception as e:
        logger.error(f"arcgis district lookup: {e}")
        return None


# ── keyboards ──────────────────────────────────────────────────────────────────

def _type_picker() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚨 Daily Crime Report",     callback_data="sub_type_crime_daily")],
        [InlineKeyboardButton("📊 Weekly District Digest", callback_data="sub_type_district_digest")],
        [InlineKeyboardButton("❌ Cancel",                  callback_data="sub_cancel")],
    ])


def _district_picker() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for d in [str(i) for i in range(1, 11)]:
        row.append(InlineKeyboardButton(f"D{d}", callback_data=f"sub_district_{d}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("📍 Enter my address instead", callback_data="sub_enter_address")])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")])
    return InlineKeyboardMarkup(rows)


# ── /subscribe ─────────────────────────────────────────────────────────────────

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text(
        "📬 *Choose an alert type:*",
        parse_mode="Markdown",
        reply_markup=_type_picker(),
    )


async def subscribe_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry from an inline button (e.g. from /crime menu)."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.reply_text(
        "📬 *Choose an alert type:*",
        parse_mode="Markdown",
        reply_markup=_type_picker(),
    )


async def choose_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    alert_type = query.data.replace("sub_type_", "")
    context.user_data[_TYPE] = alert_type
    label = ALERT_TYPES.get(alert_type, alert_type)
    desc = (
        "New incidents in your district, sent each morning"
        if alert_type == "crime_daily"
        else "Week-over-week crime summary, sent every Monday"
    )
    await query.edit_message_text(
        f"*{label}*\n_{desc}_\n\nPick your council district:",
        parse_mode="Markdown",
        reply_markup=_district_picker(),
    )


async def choose_district_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    district = query.data.replace("sub_district_", "")
    await _save_and_confirm(query.edit_message_text, context, district)


async def enter_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data[_STATE] = _AWAITING_ADDRESS
    await query.edit_message_text(
        "📍 Type your Austin street address, neighborhood, or zip code:",
        parse_mode="Markdown",
    )


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Cancelled.")


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Intercept text messages only when user is in address-entry state."""
    if context.user_data.get(_STATE) != _AWAITING_ADDRESS:
        return  # not for us — let echo handler take it

    address = update.message.text.strip()
    context.user_data.pop(_STATE, None)
    msg = await update.message.reply_text("⏳ Looking up your district...")

    district = await asyncio.to_thread(_geocode_to_district, address)

    if not district:
        await msg.edit_text(
            "📍 We couldn't pin your exact district — zip codes often cross district lines.\n\n"
            "Find yours here: [Austin Council District Map](https://www.austintexas.gov/GIS/CouncilDistrictMap)\n\n"
            "Then pick below:",
            parse_mode="Markdown",
            reply_markup=_district_picker(),
            disable_web_page_preview=True,
        )
        return

    await msg.delete()
    await _save_and_confirm(update.message.reply_text, context, district)


async def _save_and_confirm(reply_fn, context: ContextTypes.DEFAULT_TYPE, district: str) -> None:
    alert_type = context.user_data.get(_TYPE)
    if not alert_type:
        await reply_fn("Something went wrong. Please try /subscribe again.")
        return

    user_id = context._user_id
    chat_id = context._chat_id
    db.upsert_user(user_id, chat_id)
    db.add_subscription(user_id, alert_type, district)
    context.user_data.clear()

    label      = DISTRICT_LABELS.get(district, f"District {district}")
    type_label = ALERT_TYPES.get(alert_type, alert_type)
    schedule   = "each morning" if alert_type == "crime_daily" else "every Monday morning"

    await reply_fn(
        f"✅ *Subscribed!*\n\n"
        f"*Alert:* {type_label}\n"
        f"*District:* {label}\n"
        f"*Schedule:* {schedule}\n\n"
        f"Use /myalerts to manage or /unsubscribe to stop.",
        parse_mode="Markdown",
    )


# ── /myalerts ──────────────────────────────────────────────────────────────────

async def myalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = db.get_user_subscriptions(update.effective_user.id)
    if not subs:
        await update.message.reply_text(
            "You have no active alerts. Use /subscribe to set one up."
        )
        return

    keyboard, lines = [], []
    for sub in subs:
        type_label = ALERT_TYPES.get(sub["alert_type"], sub["alert_type"])
        dist_label = DISTRICT_LABELS.get(sub["district"], f"District {sub['district']}")
        short = f"{type_label} — {dist_label}"
        lines.append(f"• {short}")
        keyboard.append([InlineKeyboardButton(f"❌ Cancel: {short[:45]}", callback_data=f"unsub_{sub['id']}")])

    await update.message.reply_text(
        "📬 *Your active alerts:*\n" + "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cancel_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    sub_id = int(query.data.replace("unsub_", ""))
    removed = db.deactivate_subscription(sub_id, update.effective_user.id)
    await query.edit_message_text("✅ Alert cancelled." if removed else "Alert not found.")


# ── /unsubscribe ───────────────────────────────────────────────────────────────

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = db.deactivate_all(update.effective_user.id)
    await update.message.reply_text(
        f"✅ Cancelled {count} alert{'s' if count != 1 else ''}."
        if count else "You have no active alerts."
    )


# ── /deletedata ────────────────────────────────────────────────────────────────

async def deletedata_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.delete_user_data(update.effective_user.id)
    await update.message.reply_text(
        "🗑️ Done. All your alert preferences and stored data have been deleted."
    )


# ── handler registration ───────────────────────────────────────────────────────

def register_alert_handlers(app) -> None:
    """Register all alert handlers onto the PTB Application."""
    app.add_handler(CommandHandler("subscribe",   subscribe_command))
    app.add_handler(CommandHandler("myalerts",    myalerts_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("deletedata",  deletedata_command))

    app.add_handler(CallbackQueryHandler(subscribe_button_entry,      pattern=r"^subscribe_start$"))
    app.add_handler(CallbackQueryHandler(choose_type_callback,        pattern=r"^sub_type_"))
    app.add_handler(CallbackQueryHandler(choose_district_callback,    pattern=r"^sub_district_"))
    app.add_handler(CallbackQueryHandler(enter_address_callback,      pattern=r"^sub_enter_address$"))
    app.add_handler(CallbackQueryHandler(cancel_callback,             pattern=r"^sub_cancel$"))
    app.add_handler(CallbackQueryHandler(cancel_subscription_callback,pattern=r"^unsub_\d+$"))

    # Text handler for address input — must be group -1 to run before echo handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address), group=-1)
