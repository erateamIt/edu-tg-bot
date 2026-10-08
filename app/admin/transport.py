"""Telegram Bot API, environment-file and document transport helpers."""
import json
import logging
import os
import urllib.parse
import urllib.request
import uuid

from dotenv import dotenv_values

from app.core.config import PROJECT_ROOT

ENV_PATH = PROJECT_ROOT / ".env"
cfg = dotenv_values(ENV_PATH)
BOT_TOKEN = cfg.get("ADMIN_BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("ADMIN_BOT_TOKEN .env faylida sozlanmagan. BotFather tokenini kiriting.")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def telegram(method, data=None):
    """Telegram Bot API'ga POST so'rov yuboradi."""
    data = data or {}
    body = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        f"{API_URL}/{method}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception:
        logging.exception("Telegram API request failed: %s", method)
        return None

    if not result.get("ok"):
        logging.error("Telegram API error: %s", result)
        return None

    return result.get("result")

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard is not None:
        data["reply_markup"] = json.dumps(
            {
                "keyboard": keyboard,
                "resize_keyboard": True,
                "one_time_keyboard": False,
            },
            ensure_ascii=False,
        )

    return telegram("sendMessage", data)

def send_inline_message(chat_id, text, keyboard):
    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(
                {"inline_keyboard": keyboard},
                ensure_ascii=False,
            ),
        },
    )

def edit_inline_message(chat_id, message_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }
    if keyboard is not None:
        data["reply_markup"] = json.dumps(
            {"inline_keyboard": keyboard},
            ensure_ascii=False,
        )
    else:
        data["reply_markup"] = json.dumps({"inline_keyboard": []})
    return telegram("editMessageText", data)

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
    if show_alert:
        data["show_alert"] = "true"
    telegram("answerCallbackQuery", data)

def read_env(key, default=""):
    values = dotenv_values(ENV_PATH)
    return values.get(key, default) or default

def write_env(updates):
    """Qiymatlarni .env ga yozadi va mavjud boshqa qiymatlarni saqlab qoladi."""
    values = {}

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    for key, value in updates.items():
        values[key] = str(value)

    ENV_PATH.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )

    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass

def send_document(chat_id, filename, content, caption=""):
    """Telegram Bot API sendDocument uchun multipart/form-data yuboradi."""
    boundary = "----EducationBot" + uuid.uuid4().hex
    file_bytes = content.encode("utf-8") if isinstance(content, str) else content

    parts = []
    def field(name, value):
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        .encode("utf-8")
        )

    field("chat_id", str(chat_id))
    if caption:
        field("caption", caption)

    parts.append(
        (f"--{boundary}\r\n"
         f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
         "Content-Type: application/json\r\n\r\n").encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        f"{API_URL}/sendDocument",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception:
        logging.exception("Telegram document upload failed")
        return None

    if not result.get("ok"):
        logging.error("Telegram API error: %s", result)
        return None
    return result.get("result")
