"""Scheduled daily report generation and Telegram delivery."""
import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app import database as db
from app.core import config

from app.telegram.client import client

log = logging.getLogger("daily_reports")


async def daily_report_loop():
    while True:
        try:
            timezone_name = (
                db.get_setting("report_timezone", config.REPORT_TIMEZONE)
                or config.REPORT_TIMEZONE
            )
            report_timezone = ZoneInfo(timezone_name)
            now = datetime.now(report_timezone)
            report_time = (
                db.get_setting("report_time", config.REPORT_TIME)
                or config.REPORT_TIME
            )
            hour, minute = map(int, report_time.split(":"))
            report_day = now.date()
            if now.time() >= time(hour, minute):
                start = datetime.combine(
                    report_day, time.min, tzinfo=report_timezone
                )
                end = start + timedelta(days=1)
                if db.claim_daily_report(report_day.isoformat()):
                    stats = db.get_daily_stats(start.isoformat(), end.isoformat())
                    report = (
                        f"📊 BUGUNGI HISOBOT ({report_day.isoformat()})\n\n"
                        f"👥 Yangi mijozlar: {stats['new_customers']}\n"
                        f"💬 Kelgan xabarlar: {stats['incoming_messages']}\n"
                        f"🤖 AutoReply: {stats['auto_replies']}\n"
                        f"👨‍💼 Admin javoblari: {stats['admin_replies']}\n"
                        f"🚨 Javobsiz: {db.count_unanswered()}\n\n"
                        f"📨 Yuborilgan xabarlar: {stats['sent_messages']}\n"
                        f"🖼 Media yuborilgan: {stats['sent_media']}\n"
                        f"👥 Guruhlarga yuborilgan: {stats['group_messages']}\n\n"
                        f"📈 Eng ko‘p murojaat: {stats['top_inquiry']}\n"
                        f"🏷 Eng ko‘p tag: {stats['top_tag']}"
                    )
                    target = (
                        int(db.get_setting("report_user_id", "0") or 0)
                        or config.REPORT_USER_ID
                        or config.ADMIN_USER_ID
                        or config.ADMIN_CHAT_ID
                    )
                    if target:
                        await client.send_message(target, report)
                        db.add_log(
                            "daily_report_sent",
                            "user",
                            target,
                            {"date": report_day.isoformat()},
                        )
            await asyncio.sleep(30)
        except Exception:
            log.exception("Daily report loop error")
            await asyncio.sleep(30)
