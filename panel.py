import os
import asyncio
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

import config
import db

app = FastAPI(title="Education Telegram UserBot")

ENV_PATH = Path(".env")

def auth(x_panel_token: str | None):
    if x_panel_token != config.PANEL_TOKEN:
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

@app.on_event("startup")
async def startup():
    db.init_db()

@app.get("/", response_class=HTMLResponse)
async def dashboard(x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    customers = db.list_customers(100)
    groups = db.list_groups()
    scheduled = db.list_scheduled()
    welcome = db.get_setting("welcome_message", "")
    api_id = read_env_value("API_ID")
    api_hash = read_env_value("API_HASH")
    phone = read_env_value("PHONE_NUMBER")
    admin_id = read_env_value("ADMIN_CHAT_ID")
    monitor = db.get_setting("monitor_minutes", "5")
    panel_token = read_env_value("PANEL_TOKEN")

    rows = "".join(
        f"<tr><td>{c['telegram_id']}</td><td>{c['username'] or ''}</td>"
        f"<td>{c['first_name'] or ''} {c['last_name'] or ''}</td>"
        f"<td>{c['status']}</td><td>{c['last_message_at'] or ''}</td></tr>"
        for c in customers
    ) or "<tr><td colspan='5'>Hozircha mijoz yo‘q</td></tr>"

    grows = "".join(
        f"<tr><td>{g['title']}</td><td>{g['telegram_id']}</td>"
        f"<td>{'Yoqilgan' if g['enabled'] else 'O‘chirilgan'}</td></tr>"
        for g in groups
    ) or "<tr><td colspan='3'>Guruh topilmadi</td></tr>"

    return f"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Education Telegram UserBot</title>
<style>
*{{box-sizing:border-box}} body{{font-family:Arial,sans-serif;margin:0;background:#f4f7fb;color:#172033}}
.container{{max-width:1200px;margin:0 auto;padding:25px}}
h1{{margin-top:0}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px}}
.card{{background:#fff;padding:20px;margin:15px 0;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.06)}}
.stat{{font-size:26px;font-weight:700}} label{{display:block;font-weight:600;margin:12px 0 6px}}
input,textarea{{width:100%;padding:11px;border:1px solid #ccd3df;border-radius:8px;font-size:15px}}
textarea{{min-height:170px;resize:vertical}} button{{margin-top:15px;padding:11px 18px;border:0;border-radius:8px;background:#2563eb;color:#fff;font-weight:700;cursor:pointer}}
small{{color:#657084}} table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left}}
.note{{background:#fff8db;padding:12px;border-radius:8px;margin-top:10px}}
</style>
</head>
<body><div class="container">
<h1>🎓 Education Telegram UserBot</h1>

<div class="grid">
<div class="card"><small>Mijozlar</small><div class="stat">{len(customers)}</div></div>
<div class="card"><small>Telegram guruhlar</small><div class="stat">{len(groups)}</div></div>
<div class="card"><small>Scheduled</small><div class="stat">{len(scheduled)}</div></div>
</div>

<div class="card">
<h2>⚙️ Telegram ulanish sozlamalari</h2>
<form method="post" action="/settings">
<label>API ID</label>
<input name="api_id" value="{api_id}" placeholder="12345678" required>
<small>my.telegram.org → API development tools dan olinadi.</small>

<label>API HASH</label>
<input name="api_hash" value="{api_hash}" placeholder="Telegram API HASH" required>

<label>Telefon raqami</label>
<input name="phone_number" value="{phone}" placeholder="+998901234567" required>

<label>Admin Telegram ID</label>
<input name="admin_chat_id" value="{admin_id}" placeholder="123456789" required>
<small>5 daqiqalik javobsiz mijoz ogohlantirishi shu IDga boradi.</small>

<label>Javobsiz xabar uchun vaqt (daqiqa)</label>
<input type="number" name="monitor_minutes" value="{monitor}" min="1" max="1440">

<label>Panel token</label>
<input name="panel_token" value="{panel_token}" required>

<button type="submit">💾 Sozlamalarni saqlash</button>
</form>

<div class="note">
<b>Muhim:</b> API ID/HASH va telefon raqami <code>.env</code>ga saqlanadi.
Saqlagandan keyin <b>python bot.py</b>ni qayta ishga tushiring.
</div>
</div>

<div class="card">
<h2>💬 Birinchi murojaat uchun avtomatik xabar</h2>
<form method="post" action="/welcome">
<textarea name="welcome_message">{welcome}</textarea>
<button type="submit">💾 Avtojavobni saqlash</button>
</form>
</div>

<div class="card">
<h2>👥 Mijozlar</h2>
<table><tr><th>Telegram ID</th><th>Username</th><th>Ism</th><th>Status</th><th>Oxirgi xabar</th></tr>{rows}</table>
</div>

<div class="card">
<h2>📢 Telegram guruhlari</h2>
<table><tr><th>Guruh</th><th>ID</th><th>Holat</th></tr>{grows}</table>
</div>
</div></body></html>"""

@app.post("/settings")
async def settings_form(
    api_id: int,
    api_hash: str,
    phone_number: str,
    admin_chat_id: int,
    monitor_minutes: int = 5,
    panel_token: str = "",
    x_panel_token: str | None = Header(default=None),
):
    auth(x_panel_token)
    update_env({
        "API_ID": api_id,
        "API_HASH": api_hash,
        "PHONE_NUMBER": phone_number,
        "ADMIN_CHAT_ID": admin_chat_id,
        "MONITOR_MINUTES": monitor_minutes,
        "PANEL_TOKEN": panel_token,
    })
    db.set_setting("monitor_minutes", monitor_minutes)
    return HTMLResponse(
        "<h2>✅ Saqlandi.</h2>"
        "<p>Endi terminalda <code>Ctrl+C</code> qilib, "
        "<code>python bot.py</code>ni qayta ishga tushiring.</p>"
        "<p>Panelga qaytish: <a href='http://127.0.0.1:8000'>127.0.0.1:8000</a></p>"
    )

@app.post("/welcome")
async def welcome_form(
    welcome_message: str,
    x_panel_token: str | None = Header(default=None),
):
    auth(x_panel_token)
    db.set_setting("welcome_message", welcome_message)
    return HTMLResponse(
        "<h2>✅ Avtojavob saqlandi.</h2>"
        "<p>Panelga qayting va boshqa mijoz bilan test qiling.</p>"
        "<p><a href='http://127.0.0.1:8000'>Panelga qaytish</a></p>"
    )

@app.get("/api/customers")
async def customers(x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    return [dict(x) for x in db.list_customers(200)]

@app.get("/api/customers/{customer_id}/messages")
async def customer_messages(customer_id: int, x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    return [dict(x) for x in db.list_messages(customer_id)]

@app.get("/api/groups")
async def groups(x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    return [dict(x) for x in db.list_groups()]

@app.post("/api/groups/{telegram_id}/enable")
async def enable_group(telegram_id: int, x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    db.set_group_enabled(telegram_id, True)
    return {"ok": True}

@app.post("/api/groups/{telegram_id}/disable")
async def disable_group(telegram_id: int, x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    db.set_group_enabled(telegram_id, False)
    return {"ok": True}

@app.post("/api/settings")
async def settings_api(body: SettingBody, x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    values = {}
    if body.api_id is not None: values["API_ID"] = body.api_id
    if body.api_hash is not None: values["API_HASH"] = body.api_hash
    if body.phone_number is not None: values["PHONE_NUMBER"] = body.phone_number
    if body.admin_chat_id is not None: values["ADMIN_CHAT_ID"] = body.admin_chat_id
    if body.monitor_minutes is not None:
        values["MONITOR_MINUTES"] = body.monitor_minutes
        db.set_setting("monitor_minutes", body.monitor_minutes)
    if body.panel_token is not None: values["PANEL_TOKEN"] = body.panel_token
    if values: update_env(values)
    if body.welcome_message is not None:
        db.set_setting("welcome_message", body.welcome_message)
    return {"ok": True, "message": "Saqlangan. Telegram credentiallari uchun botni restart qiling."}

@app.post("/api/scheduled")
async def scheduled(body: ScheduleBody, x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    row_id = db.add_scheduled(body.group_telegram_id, body.text, body.run_at, body.repeat)
    return {"ok": True, "id": row_id}

@app.get("/api/scheduled")
async def scheduled_list(x_panel_token: str | None = Header(default=None)):
    auth(x_panel_token)
    return [dict(x) for x in db.list_scheduled()]
