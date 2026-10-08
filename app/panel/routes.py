"""HTTP routes for the FastAPI management panel."""
from urllib.parse import parse_qs

from fastapi import APIRouter, Cookie, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import database as db
from .services import (
    ScheduleBody,
    SettingBody,
    auth,
    create_panel_session,
    panel_token_configured,
    panel_token_matches,
    read_env_value,
    update_env,
)

router = APIRouter()


def login_page(error: str = "", status_code: int = 200) -> HTMLResponse:
    message = (
        f'<p class="error" role="alert">{error}</p>'
        if error
        else ""
    )
    configured = panel_token_configured()
    form = (
        """<form method="post" action="/login">
<label for="token">Panel token</label>
<input id="token" name="token" type="password" autocomplete="current-password"
       maxlength="4096" required autofocus>
<button type="submit">Kirish</button>
</form>"""
        if configured
        else '<p class="error" role="alert">Konfiguratsiya xatosi: PANEL_TOKEN .env faylida sozlanmagan.</p>'
    )
    return HTMLResponse(
        f"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Education Center</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;
font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
background:linear-gradient(135deg,#eef4ff,#f8fafc 55%,#e8f5f0);color:#172033}}
.login{{width:min(100%,420px);padding:38px;background:#fff;border:1px solid #e5eaf2;
border-radius:20px;box-shadow:0 20px 60px rgba(31,50,81,.12)}}
.brand{{width:48px;height:48px;display:grid;place-items:center;border-radius:14px;
background:#e8efff;color:#315ee7;font-size:24px}}
h1{{font-size:26px;margin:22px 0 8px}} p{{color:#667085;line-height:1.5}}
label{{display:block;font-weight:600;font-size:14px;margin:26px 0 8px}}
input{{width:100%;padding:13px 14px;border:1px solid #ccd5e2;border-radius:10px;
font-size:16px;outline:none}} input:focus{{border-color:#426cf5;
box-shadow:0 0 0 3px rgba(66,108,245,.14)}}
button{{width:100%;margin-top:18px;padding:13px;border:0;border-radius:10px;
background:#315ee7;color:white;font-size:15px;font-weight:700;cursor:pointer}}
button:hover{{background:#244bc4}} .error{{margin:18px 0 0;padding:12px 14px;
border-radius:10px;background:#fff0f0;color:#b42318;font-weight:600}}
</style>
</head>
<body><main class="login">
<div class="brand" aria-hidden="true">🎓</div>
<h1>Education Center</h1>
<p>Panelga kirish uchun tokenni kiriting.</p>
{message}
{form}
</main></body></html>""",
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    if not panel_token_configured():
        return login_page()
    try:
        auth(x_panel_token, panel_session)
    except HTTPException:
        return login_page()
    customers = db.list_customers(100)
    groups = db.list_groups()
    scheduled = db.list_scheduled()
    welcome = db.get_setting("welcome_message", "")
    api_id = read_env_value("API_ID")
    api_hash = read_env_value("API_HASH")
    phone = read_env_value("PHONE_NUMBER")
    admin_id = read_env_value("ADMIN_CHAT_ID")
    monitor = db.get_setting("monitor_minutes", "5")

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
<title>Education Center</title>
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
<h1>🎓 Education Center</h1>

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

<label>Yangi panel tokeni (ixtiyoriy)</label>
<input type="password" name="panel_token" value="" autocomplete="new-password"
placeholder="O‘zgartirmaslik uchun bo‘sh qoldiring">

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


@router.post("/login")
async def login(request: Request):
    if not panel_token_configured():
        return login_page(status_code=503)

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 16384:
        return login_page("Token noto'g'ri", status_code=401)
    try:
        fields = parse_qs(
            (await request.body()).decode("utf-8", errors="replace"),
            keep_blank_values=True,
            max_num_fields=10,
        )
    except ValueError:
        return login_page("Token noto'g'ri", status_code=401)
    supplied_token = fields.get("token", [""])[0]
    if len(supplied_token) > 4096 or not panel_token_matches(supplied_token):
        return login_page("Token noto'g'ri", status_code=401)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "panel_session",
        create_panel_session(),
        max_age=43200,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return response


@router.post("/settings")
async def settings_form(
    api_id: int,
    api_hash: str,
    phone_number: str,
    admin_chat_id: int,
    monitor_minutes: int = 5,
    panel_token: str = "",
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    values = {
        "API_ID": api_id,
        "API_HASH": api_hash,
        "PHONE_NUMBER": phone_number,
        "ADMIN_CHAT_ID": admin_chat_id,
        "MONITOR_MINUTES": monitor_minutes,
    }
    if panel_token:
        values["PANEL_TOKEN"] = panel_token
    update_env(values)
    db.set_setting("monitor_minutes", monitor_minutes)
    return HTMLResponse(
        "<h2>✅ Saqlandi.</h2>"
        "<p>Endi terminalda <code>Ctrl+C</code> qilib, "
        "<code>python bot.py</code>ni qayta ishga tushiring.</p>"
        "<p>Panelga qaytish: <a href='http://127.0.0.1:8000'>127.0.0.1:8000</a></p>"
    )

@router.post("/welcome")
async def welcome_form(
    welcome_message: str,
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    db.set_setting("welcome_message", welcome_message)
    return HTMLResponse(
        "<h2>✅ Avtojavob saqlandi.</h2>"
        "<p>Panelga qayting va boshqa mijoz bilan test qiling.</p>"
        "<p><a href='http://127.0.0.1:8000'>Panelga qaytish</a></p>"
    )

@router.get("/api/customers")
async def customers(
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    return [dict(x) for x in db.list_customers(200)]

@router.get("/api/customers/{customer_id}/messages")
async def customer_messages(
    customer_id: int,
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    return [dict(x) for x in db.list_messages(customer_id)]

@router.get("/api/groups")
async def groups(
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    return [dict(x) for x in db.list_groups()]

@router.post("/api/groups/{telegram_id}/enable")
async def enable_group(
    telegram_id: int,
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    db.set_group_enabled(telegram_id, True)
    return {"ok": True}

@router.post("/api/groups/{telegram_id}/disable")
async def disable_group(
    telegram_id: int,
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    db.set_group_enabled(telegram_id, False)
    return {"ok": True}

@router.post("/api/settings")
async def settings_api(
    body: SettingBody,
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    values = {}
    if body.api_id is not None: values["API_ID"] = body.api_id
    if body.api_hash is not None: values["API_HASH"] = body.api_hash
    if body.phone_number is not None: values["PHONE_NUMBER"] = body.phone_number
    if body.admin_chat_id is not None: values["ADMIN_CHAT_ID"] = body.admin_chat_id
    if body.monitor_minutes is not None:
        values["MONITOR_MINUTES"] = body.monitor_minutes
        db.set_setting("monitor_minutes", body.monitor_minutes)
    if body.panel_token: values["PANEL_TOKEN"] = body.panel_token
    if values: update_env(values)
    if body.welcome_message is not None:
        db.set_setting("welcome_message", body.welcome_message)
    return {"ok": True, "message": "Saqlangan. Telegram credentiallari uchun botni restart qiling."}

@router.post("/api/scheduled")
async def scheduled(
    body: ScheduleBody,
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    row_id = db.add_scheduled(body.group_telegram_id, body.text, body.run_at, body.repeat)
    return {"ok": True, "id": row_id}

@router.get("/api/scheduled")
async def scheduled_list(
    x_panel_token: str | None = Header(default=None),
    panel_session: str | None = Cookie(default=None),
):
    auth(x_panel_token, panel_session)
    return [dict(x) for x in db.list_scheduled()]
