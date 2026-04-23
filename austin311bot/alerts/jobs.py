"""Background alert jobs: crime_daily and district_digest."""

import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from alerts import db

logger = logging.getLogger(__name__)

CRIME_URL = "https://data.austintexas.gov/resource/fdj4-gpfu.json"
CRIME_MAP_URL = "https://austin311.com/crime/"

DISTRICT_LABELS = {
    "1": "District 1", "2": "District 2", "3": "District 3",
    "4": "District 4", "5": "District 5", "6": "District 6",
    "7": "District 7", "8": "District 8", "9": "District 9",
    "10": "District 10",
}


def _headers() -> dict:
    token = os.getenv("AUSTIN_APP_TOKEN", "")
    return {"X-App-Token": token} if token else {}


def _fetch_district_crimes(district: str, start: datetime, end: datetime) -> list[dict]:
    start_s = start.strftime("%Y-%m-%dT%H:%M:%S")
    end_s   = end.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        resp = requests.get(
            CRIME_URL,
            params={
                "$where": (
                    f"council_district='{district}' "
                    f"AND rep_date >= '{start_s}' "
                    f"AND rep_date < '{end_s}'"
                ),
                "$limit": 2000,
                "$select": "incident_report_number,crime_type,rep_date",
            },
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"crime fetch district={district}: {e}")
        return []


def _type_breakdown(rows: list[dict], top_n: int = 5) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        ct = (r.get("crime_type") or "Unknown").title()
        counts[ct] = counts.get(ct, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1])[:top_n])


# ── daily crime alert ──────────────────────────────────────────────────────────

async def crime_daily_job(context) -> None:
    """Send a daily digest of new incidents for each crime_daily subscription."""
    db.prune_sent_log()
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    today_str = now.strftime("%Y-%m-%d")

    subs = db.get_active_subscriptions("crime_daily")
    if not subs:
        return

    # Cache per district to avoid duplicate API calls for same district
    district_cache: dict[str, list[dict]] = {}

    for sub in subs:
        sub_id   = sub["id"]
        district = sub["district"]
        chat_id  = sub["chat_id"]
        send_key = f"{today_str}"

        if db.already_sent(sub_id, send_key):
            continue

        if district not in district_cache:
            district_cache[district] = _fetch_district_crimes(district, yesterday, now)

        rows = district_cache[district]
        label = DISTRICT_LABELS.get(district, f"District {district}")

        if not rows:
            # Still mark sent so we don't hammer the API tomorrow with no-data subs
            db.mark_sent(sub_id, send_key)
            continue

        breakdown = _type_breakdown(rows)
        lines = "\n".join(f"  • {ct}: {cnt}" for ct, cnt in breakdown.items())
        others = len(rows) - sum(breakdown.values())
        if others > 0:
            lines += f"\n  • Other: {others}"

        msg = (
            f"🚨 *{label} — Daily Crime Report*\n"
            f"_{yesterday.strftime('%b %-d')} incidents newly reported_\n\n"
            f"*{len(rows)}* incident{'s' if len(rows) != 1 else ''} filed:\n"
            f"{lines}\n\n"
            f"[Full crime map →]({CRIME_MAP_URL})\n"
            f"_/myalerts to manage · /unsubscribe to stop_"
        )

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            db.mark_sent(sub_id, send_key)
        except Exception as e:
            logger.error(f"crime_daily send sub={sub_id}: {e}")


# ── weekly district digest ─────────────────────────────────────────────────────

async def district_digest_job(context) -> None:
    """Send a weekly crime digest for each district_digest subscription."""
    db.prune_sent_log()
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)
    week_key = week_start.strftime("%Y-W%U")

    subs = db.get_active_subscriptions("district_digest")
    if not subs:
        return

    district_cache: dict[str, tuple[list, list]] = {}

    for sub in subs:
        sub_id   = sub["id"]
        district = sub["district"]
        chat_id  = sub["chat_id"]

        if db.already_sent(sub_id, week_key):
            continue

        if district not in district_cache:
            this_week = _fetch_district_crimes(district, week_start, now)
            last_week = _fetch_district_crimes(district, prev_start, week_start)
            district_cache[district] = (this_week, last_week)

        this_week, last_week = district_cache[district]
        label = DISTRICT_LABELS.get(district, f"District {district}")

        this_n = len(this_week)
        last_n = len(last_week)

        if this_n == 0 and last_n == 0:
            db.mark_sent(sub_id, week_key)
            continue

        # Week-over-week change
        if last_n > 0:
            pct = round((this_n - last_n) / last_n * 100)
            arrow = "📈" if pct > 5 else "📉" if pct < -5 else "➡️"
            trend = f"{arrow} {'+' if pct > 0 else ''}{pct}% vs last week ({last_n})"
        else:
            trend = f"📊 {this_n} incidents (no prior week data)"

        breakdown = _type_breakdown(this_week, top_n=5)
        lines = "\n".join(
            f"  {i+1}. {ct}: {cnt} ({round(cnt/this_n*100)}%)"
            for i, (ct, cnt) in enumerate(breakdown.items())
        )

        date_range = f"{week_start.strftime('%b %-d')}–{now.strftime('%b %-d, %Y')}"
        msg = (
            f"📊 *{label} — Weekly Crime Digest*\n"
            f"_{date_range}_\n\n"
            f"*{this_n}* incident{'s' if this_n != 1 else ''} reported\n"
            f"{trend}\n\n"
            f"*Top offense types:*\n{lines}\n\n"
            f"[Full crime map →]({CRIME_MAP_URL})\n"
            f"_/myalerts to manage · /unsubscribe to stop_"
        )

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            db.mark_sent(sub_id, week_key)
        except Exception as e:
            logger.error(f"district_digest send sub={sub_id}: {e}")
