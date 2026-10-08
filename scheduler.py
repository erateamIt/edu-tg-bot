import asyncio
from datetime import datetime, timedelta, timezone

import db

async def scheduler_loop(client):
    """PostgreSQL'dagi scheduled_messages jadvalini tekshiradi va xabarlarni yuboradi."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            rows = db.due_scheduled(now.isoformat())

            for row in rows:
                try:
                    await client.send_message(row["group_telegram_id"], row["text"])
                    db.mark_scheduled_run(row["id"], row["run_at"])

                    repeat = row["repeat"].lower()
                    if repeat == "once":
                        db.disable_scheduled(row["id"])
                    elif repeat in ("daily", "weekly"):
                        current = datetime.fromisoformat(row["run_at"]).astimezone(timezone.utc)
                        next_run = current + timedelta(days=1 if repeat == "daily" else 7)
                        db.reschedule_scheduled(row["id"], next_run.isoformat())
                except Exception:
                    import logging
                    logging.getLogger("scheduler").exception(
                        "Scheduled message failed: id=%s", row["id"]
                    )
        except Exception:
            import logging
            logging.getLogger("scheduler").exception("Scheduler loop error")

        await asyncio.sleep(10)
