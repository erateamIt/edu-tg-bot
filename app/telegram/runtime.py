"""UserBot startup and background-worker lifecycle."""
import asyncio
import logging

from app import database as db
from app.core import config
from app.core.logging_config import configure_logging
from app.scheduler.reports import daily_report_loop
from app.scheduler.worker import scheduler_loop
from .client import client
from .groups import sync_groups
from . import handlers as _registered_handlers
from .messaging import group_message_job_loop, outgoing_message_loop
from .monitoring import monitor_loop
from .qr_login import login_with_qr

log = logging.getLogger("userbot")

async def main():
    db.init_db()
    await login_with_qr()
    me = await client.get_me()
    log.info("Telegram connected as %s (%s)", getattr(me, "username", None), me.id)
    await sync_groups()
    asyncio.create_task(monitor_loop())
    asyncio.create_task(scheduler_loop(client))
    asyncio.create_task(group_message_job_loop())
    asyncio.create_task(outgoing_message_loop())
    asyncio.create_task(daily_report_loop())

    print("UserBot ishga tushdi.")
    print("Session:", config.SESSION_NAME + ".session")
    await client.run_until_disconnected()


def run():
    configure_logging()
    asyncio.run(main())
