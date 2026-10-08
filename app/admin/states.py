"""Volatile per-user Admin Bot workflow state."""

from app.core.config import PROJECT_ROOT

STATES = {}
GROUP_SELECTIONS = {}
GROUP_MESSAGE_STATES = {}
WORKFLOWS = {}
MEDIA_DIR = PROJECT_ROOT / "media_queue"
