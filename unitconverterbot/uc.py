import os
import re
import logging
from datetime import datetime
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, InlineQueryHandler, filters, ContextTypes
from pint import UnitRegistry, UndefinedUnitError, DimensionalityError
import pytz

logging.basicConfig(level=logging.INFO)
ureg = UnitRegistry()

START_TEXT = """
👋 *Welcome to Unit Converter Bot!*

Send a message in this format:
`[value] [unit] to [unit]`

*Quick examples:*
• `100 kg to lbs`
• `72 fahrenheit to celsius`
• `60 mph to kph`
• `3pm EST to PST`

Type /help to see all supported units and categories.
"""

HELP_TEXT = """
*Unit Converter Bot — Reference*

*Format:* `[value] [unit] to [unit]`

─────────────────────
⚖️ *Weight*
`100 kg to lbs` • `8 oz to grams`
`12 stone to kg` • `1 metric_ton to lbs`

📏 *Length*
`5 feet to meters` • `1 mile to km`
`30 cm to inches` • `100 yards to meters`
`10 nautical_miles to km`

🌡️ *Temperature*
`72 fahrenheit to celsius`
`100 celsius to fahrenheit`
`300 kelvin to celsius`

🚗 *Speed*
`60 mph to kph` • `100 kph to mph`
`20 knots to mph` • `1 mach to mph`

🧪 *Volume*
`500 ml to cups` • `1 gallon to liters`
`2 pints to ml` • `3 tablespoons to ml`
`8 fl_oz to ml`

📐 *Area*
`1000 sq_ft to sq_meters`
`10 acres to hectares`

⚡ *Energy & Power*
`500 kcal to kJ` • `100 horsepower to watts`
`1 kWh to joules` • `30 psi to bar`

💾 *Data*
`2 GB to MB` • `1 TB to GB`

⏱ *Time*
`2.5 hours to minutes` • `7 days to hours`
`4 weeks to days` • `1 year to days`

─────────────────────
🕐 *Time Zones*
`3pm EST to PST`
`15:30 GMT to JST`
`now UTC to America/New_York`
`9am PST to CET`

*Supported TZ codes:* EST, PST, CST, MST, GMT, UTC, BST, CET, JST, IST, AEST
*Full names also work:* America/New_York, Europe/London, Asia/Tokyo

─────────────────────
*Inline mode* — use in any chat:
`@botname 100 kg to lbs`

/help — show this message
"""

FORMAT_ERROR_TEXT = """
I didn't understand that. Use this format:

`[value] [unit] to [unit]`

*Examples:*
• `100 kg to lbs`
• `72 fahrenheit to celsius`
• `60 mph to kph`
• `500 ml to cups`
• `3pm EST to PST`

Type /help for all supported units.
"""

UNIT_ALIASES = {
    "kph": "km/h",
    "mph": "mi/h",
    "celsius": "degC",
    "fahrenheit": "degF",
    "kelvin": "kelvin",
    "c": "degC",
    "f": "degF",
    "k": "kelvin",
    "lbs": "lb",
    "pounds": "lb",
    "pound": "lb",
    "kilograms": "kg",
    "kilogram": "kg",
    "grams": "g",
    "gram": "g",
    "ounces": "oz",
    "ounce": "oz",
    "meters": "m",
    "meter": "m",
    "feet": "ft",
    "foot": "ft",
    "inches": "inch",
    "miles": "mi",
    "mile": "mi",
    "kilometers": "km",
    "kilometer": "km",
    "liters": "L",
    "liter": "L",
    "litres": "L",
    "litre": "L",
    "milliliters": "mL",
    "milliliter": "mL",
    "gallons": "gallon",
    "pints": "pint",
    "cups": "cup",
}

TIMEZONE_ALIASES = {
    "est": "US/Eastern",
    "edt": "US/Eastern",
    "pst": "US/Pacific",
    "pdt": "US/Pacific",
    "cst": "US/Central",
    "cdt": "US/Central",
    "mst": "US/Mountain",
    "mdt": "US/Mountain",
    "gmt": "GMT",
    "utc": "UTC",
    "bst": "Europe/London",
    "cet": "Europe/Paris",
    "jst": "Asia/Tokyo",
    "ist": "Asia/Kolkata",
    "aest": "Australia/Sydney",
    "aedt": "Australia/Sydney",
}

def normalize(unit: str) -> str:
    return UNIT_ALIASES.get(unit.lower(), unit)

def normalize_timezone(tz: str) -> str:
    return TIMEZONE_ALIASES.get(tz.lower(), tz)

def convert_timezone(text: str) -> str:
    # Pattern for time conversion: "3pm EST to PST", "15:30 GMT to JST", "now UTC to America/New_York"
    # Requires either "now" or a proper time format (HH:MM or H{am/pm}) followed by timezone names
    time_pattern = r"^(now|\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\s+(.+?)\s+(?:to|in|->|→)\s+(.+)$"
    match = re.match(time_pattern, text.strip(), re.IGNORECASE)
    if not match:
        return None

    time_str, from_tz, to_tz = match.groups()
    from_tz = normalize_timezone(from_tz.strip())
    to_tz = normalize_timezone(to_tz.strip())
    
    try:
        # Validate timezones
        if from_tz not in pytz.all_timezones:
            return f"Unknown timezone: {from_tz}"
        if to_tz not in pytz.all_timezones:
            return f"Unknown timezone: {to_tz}"
        
        from_tz_obj = pytz.timezone(from_tz)
        to_tz_obj = pytz.timezone(to_tz)
        
        # Parse time
        if time_str.lower() == "now":
            now = datetime.now(from_tz_obj)
        else:
            # Determine if AM/PM is present
            has_ampm = bool(re.search(r'(am|pm)', time_str, re.IGNORECASE))
            if has_ampm:
                # Format like "3pm" or "3:30pm"
                if ":" in time_str:
                    time_format = "%I:%M%p"
                else:
                    time_format = "%I%p"
                time_obj = datetime.strptime(time_str.lower(), time_format).time()
                now = datetime.now(from_tz_obj).replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
            else:
                # Format like "15:30" or "15"
                if ":" in time_str:
                    time_format = "%H:%M"
                else:
                    time_format = "%H"
                time_obj = datetime.strptime(time_str, time_format).time()
                now = datetime.now(from_tz_obj).replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        
        # Convert timezone
        converted_time = now.astimezone(to_tz_obj)
        
        # Format result
        from_time_str = now.strftime("%I:%M %p").lstrip("0")
        to_time_str = converted_time.strftime("%I:%M %p").lstrip("0")
        from_date = now.strftime("%Y-%m-%d")
        to_date = converted_time.strftime("%Y-%m-%d")
        
        if from_date == to_date:
            return f"{from_time_str} {from_tz} = *{to_time_str} {to_tz}*"
        else:
            return f"{from_time_str} {from_tz} ({from_date}) = *{to_time_str} {to_tz} ({to_date})*"
            
    except Exception as e:
        return f"Time conversion error: {e}"

def parse_and_convert(text: str) -> str:
    # Try timezone conversion first
    timezone_result = convert_timezone(text)
    if timezone_result:
        return timezone_result
    
    # Fall back to unit conversion
    pattern = r"^([\d.,]+)\s+(.+?)\s+(?:to|in|->|→)\s+(.+)$"
    match = re.match(pattern, text.strip(), re.IGNORECASE)
    if not match:
        return None

    value_str, from_unit_raw, to_unit_raw = match.groups()
    value = float(value_str.replace(",", ""))
    from_unit_display = from_unit_raw.strip()
    to_unit_display = to_unit_raw.strip()
    from_unit = normalize(from_unit_display)
    to_unit = normalize(to_unit_display)

    try:
        qty = ureg.Quantity(value, from_unit)
        result = qty.to(to_unit)
        result_val = result.magnitude
        if abs(result_val) >= 1000 or (abs(result_val) < 0.01 and result_val != 0):
            formatted = f"{result_val:,.4g}"
        else:
            formatted = f"{result_val:,.4f}".rstrip("0").rstrip(".")
        return f"{value:g} {from_unit_display} = *{formatted} {to_unit_display}*"
    except DimensionalityError:
        return f"Cannot convert {from_unit} to {to_unit} — incompatible units."
    except UndefinedUnitError as e:
        return f"Unknown unit: {e}"
    except Exception as e:
        return f"Error: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(START_TEXT, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

INLINE_EXAMPLES = [
    ("hint_weight",   "⚖️ Weight",      "100 kg to lbs",            "Convert 100 kg to pounds"),
    ("hint_temp",     "🌡️ Temperature", "72 fahrenheit to celsius",  "Convert 72°F to Celsius"),
    ("hint_speed",    "🚗 Speed",        "60 mph to kph",             "Convert 60 mph to km/h"),
    ("hint_volume",   "🧪 Volume",       "1 gallon to liters",        "Convert 1 gallon to liters"),
    ("hint_length",   "📏 Length",       "5 feet to meters",          "Convert 5 feet to meters"),
    ("hint_timezone", "🕐 Time Zone",    "3pm EST to PST",            "Convert 3 PM Eastern to Pacific"),
    ("hint_data",     "💾 Data",         "2 GB to MB",                "Convert 2 GB to megabytes"),
    ("hint_energy",   "⚡ Energy",       "500 kcal to kJ",            "Convert 500 kcal to kilojoules"),
]

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        results = [
            InlineQueryResultArticle(
                id=item_id,
                title=f"{emoji} — e.g. {example}",
                description=desc,
                input_message_content=InputTextMessageContent(example),
            )
            for item_id, emoji, example, desc in INLINE_EXAMPLES
        ]
        await update.inline_query.answer(results, cache_time=0)
        return

    result = parse_and_convert(query)
    if result is None:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="Format: [value] [unit] to [unit]",
                description="e.g.  100 kg to lbs  •  3pm EST to PST  •  72 fahrenheit to celsius",
                input_message_content=InputTextMessageContent(
                    "Format: `[value] [unit] to [unit]`\n\nExamples:\n• `100 kg to lbs`\n• `72 fahrenheit to celsius`\n• `3pm EST to PST`",
                    parse_mode="Markdown",
                ),
            )
        ]
    else:
        plain = result.replace("*", "")
        results = [
            InlineQueryResultArticle(
                id="result",
                title=plain,
                description=query,
                input_message_content=InputTextMessageContent(result, parse_mode="Markdown"),
            )
        ]

    await update.inline_query.answer(results, cache_time=30)

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    result = parse_and_convert(text)
    if result is None:
        await update.message.reply_text(FORMAT_ERROR_TEXT, parse_mode="Markdown")
    else:
        await update.message.reply_text(result, parse_mode="Markdown")

def build_app():
    token = os.environ["UC_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, convert))
    return app


def main():
    build_app().run_polling()

if __name__ == "__main__":
    main()
