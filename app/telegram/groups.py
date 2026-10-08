"""Group discovery and group-message queue processing."""
import logging

from app import database as db
from telethon.tl.types import Channel, Chat

from .client import client

log = logging.getLogger("userbot")

async def sync_groups():
    try:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if is_group_entity(entity):
                db.sync_group(
                    dialog.id,
                    getattr(entity, "title", None) or dialog.name or str(dialog.id),
                    getattr(entity, "username", None),
                )
        log.info("Telegram groups synchronized.")
    except Exception:
        log.exception("Group synchronization failed")

def is_group_entity(entity):
    return isinstance(entity, Chat) or (
        isinstance(entity, Channel) and bool(entity.megagroup)
    )

async def group_chat_action_handler(event):
    try:
        entity = await event.get_chat()
        if is_group_entity(entity):
            db.sync_group(
                event.chat_id,
                getattr(entity, "title", None) or str(event.chat_id),
                getattr(entity, "username", None),
            )
    except Exception:
        log.exception("Group membership synchronization failed")
