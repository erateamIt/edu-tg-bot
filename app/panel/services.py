"""Authentication and environment-file services for the web panel."""
import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException
from pydantic import BaseModel

from app.core.config import PANEL_TOKEN, PROJECT_ROOT

ENV_PATH = PROJECT_ROOT / ".env"
_SESSION_SECRET = secrets.token_bytes(32)


def panel_token_configured() -> bool:
    return bool(PANEL_TOKEN)


def panel_token_matches(token: str) -> bool:
    return panel_token_configured() and hmac.compare_digest(token, PANEL_TOKEN)


def create_panel_session() -> str:
    return hmac.new(
        _SESSION_SECRET, b"education-center-panel-session", hashlib.sha256
    ).hexdigest()


def is_valid_panel_session(session: str | None) -> bool:
    return bool(session) and hmac.compare_digest(session, create_panel_session())


def auth(x_panel_token: str | None, panel_session: str | None = None):
    if not panel_token_configured():
        raise HTTPException(
            status_code=503,
            detail="Panel configuration error: PANEL_TOKEN is not set in .env",
        )
    if not (x_panel_token and panel_token_matches(x_panel_token)) and not is_valid_panel_session(panel_session):
        raise HTTPException(status_code=401, detail="Invalid panel token")

def read_env_value(key, default=""):
    if not ENV_PATH.exists():
        return default
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip()
    return default

def update_env(values: dict):
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    existing.update({k: str(v) for k, v in values.items() if v is not None})
    content = "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass

class SettingBody(BaseModel):
    api_id: int | None = None
    api_hash: str | None = None
    phone_number: str | None = None
    admin_chat_id: int | None = None
    monitor_minutes: int | None = None
    panel_token: str | None = None
    welcome_message: str | None = None

class ScheduleBody(BaseModel):
    group_telegram_id: int
    text: str
    run_at: str
    repeat: str = "once"
