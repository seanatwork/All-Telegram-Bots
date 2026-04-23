"""Telegram handlers for alert subscription management.

Commands registered:
  /subscribe   — start subscription flow (ConversationHandler)
  /myalerts    — list active subscriptions
  /unsubscribe — cancel one or all
  /deletedata  — wipe all stored data for this user
"""

import logging
import os

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from alerts import db

logger = logging.getLogger(__name__)

# ConversationHandler states
CHOOSE_TYPE, CHOOSE_DISTRICT, AWAIT_ADDRESS = range(3)

ALERT_TYPES = {
    "crime_daily":      ("🚨 Daily Crime Report", "New incidents in your district, sent each morning"),
    "district_digest":  ("📊 Weekly District Digest", "Week-over-week crime summary, sent every Monday"),
}

DISTRICTS = [str(i) for i in range(1, 11)]

DISTRICT_LABELS = {
    "1": "District 1 (NE Austin)",
    "2": "District 2 (SE Austin)",
    "3": "District 3 (E Austin / Cesar Chavez)",
    "4": "District 4 (S Austin / Oltorf)",
    "5": "District 5 (S Austin / Slaughter)",
    "6": "District 6 (NW / Jollyville)",
    "7": "District 7 (N Central / Crestview)",
    "8": "District 8 (SW / Oak Hill)",
    "9": "District 9 (Central / Downtown)",
    "10": "District 10 (W Austin / Westlake Hills)",
}


# ── geocoding ──────────────────────────────────────────────────────────────────

def _geocode_to_district(address: str) -> str | None:
    """Geocode an address string → Austin council district number, or None."""
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not maps_key:
        return None

    # Step 1: address → lat/lon
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

    # Step 2: lat/lon → council district via ArcGIS point-in-polygon
    try:
        arcgis = requests.get(
            "https://services.arcgis.com/0L95CJ0VTaxqcmED/ArcGIS/rest/services"
            "/Council_Districts/FeatureServer/0/query",
            params={
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "COUNCIL_DI",
                "f": "json",
            },
            timeout=10,
        ).json()
        features = arcgis.get("features", [])
        if not features:
            return None
        return str(features[0]["attributes"]["COUNCIL_DI"])
    except Exception as e:
        logger.error(f"arcgis district lookup: {e}")
        return None


# ── /subscribe flow ────────────────────────────────────────────────────────────

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton(
            f"{emoji} {label}",
            callback_data=f"sub_type_{key}",
        )]
        for key, (label, emoji) in [
            ("crime_daily",     ("Daily Crime Report",    "🚨")),
            ("district_digest", ("Weekly District Digest","📊")),
        ]
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")])
    await update.message.reply_text(
        "📬 *Choose an alert type:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_TYPE


async def choose_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "sub_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    alert_type = query.data.replace("sub_type_", "")
    context.user_data["alert_type"] = alert_type
    label, desc = ALERT_TYPES[alert_type]

    keyboard = _district_keyboard()
    keyboard.append([InlineKeyboardButton("📍 Enter my address instead", callback_data="sub_enter_address")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")])

    await query.edit_message_text(
        f"*{label}*\n_{desc}_\n\nPick your council district:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_DISTRICT


def _district_keyboard() -> list[list[InlineKeyboardButton]]:
    row = []
    rows = []
    for d in DISTRICTS:
        row.append(InlineKeyboardButton(f"D{d}", callback_data=f"sub_district_{d}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


async def choose_district_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "sub_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    if query.data == "sub_enter_address":
        await query.edit_message_text(
            "📍 Type your Austin street address or neighborhood\n"
            "_(e.g. '6th & Lamar' or '78704')_",
            parse_mode="Markdown",
        )
        return AWAIT_ADDRESS

    district = query.data.replace("sub_district_", "")
    return await _save_subscription(update, context, district, edit=True)


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address = update.message.text.strip()
    msg = await update.message.reply_text("⏳ Looking up your district...")

    district = await context.application.run_in_executor(None, _geocode_to_district, address)

    if not district:
        await msg.edit_text(
            "❌ Couldn't find that address. Try a street name, intersection, or zip code.\n"
            "Or use /subscribe and pick your district directly."
        )
        return ConversationHandler.END

    context.user_data["geocoded_address"] = address
    await msg.delete()
    return await _save_subscription(update, context, district, edit=False)


async def _save_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    district: str,
    edit: bool,
) -> int:
    alert_type = context.user_data.get("alert_type")
    user = update.effective_user
    chat_id = update.effective_chat.id

    db.upsert_user(user.id, chat_id)
    db.add_subscription(user.id, alert_type, district)

    label = DISTRICT_LABELS.get(district, f"District {district}")
    type_label, _ = ALERT_TYPES[alert_type]
    schedule = "each morning" if alert_type == "crime_daily" else "every Monday morning"

    text = (
        f"✅ *Subscribed!*\n\n"
        f"*Alert:* {type_label}\n"
        f"*District:* {label}\n"
        f"*Schedule:* {schedule}\n\n"
        f"Use /myalerts to manage or /unsubscribe to stop."
    )

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


# ── /myalerts ──────────────────────────────────────────────────────────────────

async def myalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = db.get_user_subscriptions(update.effective_user.id)
    if not subs:
        await update.message.reply_text(
            "You have no active alerts. Use /subscribe to set one up."
        )
        return

    type_labels = {k: v[0] for k, v in ALERT_TYPES.items()}
    keyboard = []
    lines = []
    for sub in subs:
        label = f"{type_labels.get(sub['alert_type'], sub['alert_type'])} — {DISTRICT_LABELS.get(sub['district'], 'District ' + sub['district'])}"
        lines.append(f"• {label}")
        keyboard.append([
            InlineKeyboardButton(f"❌ Cancel: {label[:40]}", callback_data=f"unsub_{sub['id']}")
        ])

    msg = "📬 *Your active alerts:*\n" + "\n".join(lines)
    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cancel_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    sub_id = int(query.data.replace("unsub_", ""))
    removed = db.deactivate_subscription(sub_id, update.effective_user.id)
    if removed:
        await query.edit_message_text("✅ Alert cancelled.")
    else:
        await query.edit_message_text("That alert wasn't found.")


# ── /unsubscribe ───────────────────────────────────────────────────────────────

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = db.deactivate_all(update.effective_user.id)
    if count:
        await update.message.reply_text(f"✅ Cancelled {count} alert{'s' if count != 1 else ''}.")
    else:
        await update.message.reply_text("You have no active alerts.")


# ── /deletedata ────────────────────────────────────────────────────────────────

async def deletedata_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.delete_user_data(update.effective_user.id)
    await update.message.reply_text(
        "🗑️ Done. All your alert preferences and stored data have been deleted."
    )


# ── conversation handler factory ───────────────────────────────────────────────

def build_subscribe_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe_command)],
        states={
            CHOOSE_TYPE: [
                CallbackQueryHandler(choose_type_callback, pattern=r"^sub_(type_|cancel)"),
            ],
            CHOOSE_DISTRICT: [
                CallbackQueryHandler(choose_district_callback, pattern=r"^sub_(district_|enter_address|cancel)"),
            ],
            AWAIT_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_message=False,
    )
