"""Register Telethon events on the one shared UserBot client."""
from telethon import events

from .client import client
from .customers import incoming_handler
from .groups import group_chat_action_handler
from .messaging import outgoing_handler

client.add_event_handler(incoming_handler, events.NewMessage(incoming=True))
client.add_event_handler(outgoing_handler, events.NewMessage(outgoing=True))
client.add_event_handler(group_chat_action_handler, events.ChatAction())
