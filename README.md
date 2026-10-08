# Education Telegram UserBot

Django ishlatilmaydi.

Stack:
- Telethon — Telegram UserBot
- PostgreSQL — asosiy database
- FastAPI — oddiy admin/API panel
- Async scheduler — PostgreSQL jadvalidagi bir martalik, kunlik va haftalik xabarlar

## 1. Virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## PostgreSQL

Ubuntu'da PostgreSQL o'rnatish:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```

PostgreSQL user va database yarating:

```bash
sudo -u postgres psql
```

```sql
CREATE USER education_user WITH PASSWORD 'KUCHLI_PAROL';
CREATE DATABASE education_center OWNER education_user;
\q
```

`.env`da:

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=education_center
DB_USER=education_user
DB_PASSWORD=KUCHLI_PAROL
```

Python kutubxonasi:

```bash
pip install -r requirements.txt
```

### Database'ni noldan yaratish

Quyidagi amallar `education_center` database'idagi barcha ma'lumotlarni
butunlay o'chiradi. Kerakli ma'lumotlar bo'lsa, avval backup oling. Avval bot,
panel va admin bot kabi database ishlatayotgan jarayonlarni to'xtating.

```bash
sudo -u postgres dropdb --if-exists education_center
sudo -u postgres createdb --owner=education_user education_center
```

`.env` ichidagi `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
qiymatlari PostgreSQL sozlamalariga mosligini tekshirib, loyiha root
papkasidan ishga tushiring:

```bash
source venv/bin/activate
python bot.py
```

`bot.py` boshlanganda `db.init_db()` chaqirilib, `customers`, `messages`,
`groups_`, `scheduled_messages`, `settings` jadvallari yaratiladi. Telegram
QR login va `education_center.session` Telethon session avvalgidek ishlaydi.

Schema turlarini tekshirish uchun:

```bash
sudo -u postgres psql -d education_center -c "
SELECT table_name, column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (table_name, column_name) IN (
    ('messages', 'answered'),
    ('messages', 'auto_reply'),
    ('groups_', 'enabled'),
    ('scheduled_messages', 'enabled')
  )
ORDER BY table_name, column_name;"
```

To'rtta ustunning `data_type` qiymati `boolean` bo'lishi kerak.

Agar eski `data.sqlite3` ma'lumotlari bo'lsa, bir marta:

```bash
python migrate_sqlite_to_postgres.py
```

## 2. Environment

```bash
cp .env.example .env
nano .env
```

`API_ID` va `API_HASH`ni https://my.telegram.org dan oling.

`ADMIN_CHAT_ID`ga monitoring xabarlari boradigan Telegram ID yozing.

## 3. UserBotni ishga tushirish

```bash
source .venv/bin/activate
python bot.py
```

Birinchi ishga tushishda Telegram login kodi va 2FA paroli so‘ralishi mumkin.
Session fayl yaratiladi. Uni hech qayerga yubormang.

## 4. Panel

Ikkinchi terminal:

```bash
source .venv/bin/activate
python run_panel.py
```

Panel:
http://127.0.0.1:8000

Panel API'lariga `X-Panel-Token` header orqali kiriladi.

Misol:

```bash
curl -H "X-Panel-Token: change-this-token" http://127.0.0.1:8000/api/customers
```

## Muhim

- `.env`ni GitHubga yubormang.
- `*.session`ni GitHubga yubormang.
- Faqat o‘zingiz boshqaradigan guruhlarga scheduled message yoqing.
- Telegram flood limitlariga rioya qiling.

## Scheduled message

API orqali:

```bash
curl -X POST \
  -H "X-Panel-Token: change-this-token" \
  -H "Content-Type: application/json" \
  -d '{"group_telegram_id":-1001234567890,"text":"Ertaga dars 18:00 da.","run_at":"2026-10-08T10:00:00+00:00","repeat":"once"}' \
  http://127.0.0.1:8000/api/scheduled
```

`repeat`:
- `once`
- `daily`
- `weekly`

Scheduler har 10 soniyada due xabarlarni tekshiradi.


## Admin panelda sozlash

Panel API header talab qilgani sababli brauzerga oddiy URL bilan kirish hozircha token bermaydi.
Terminaldan dashboardni ko‘rish:

```bash
curl -H "X-Panel-Token: YOUR_PANEL_TOKEN" http://127.0.0.1:8000
```

Panelning keyingi versiyasida form-login qo‘shish mumkin. Hozir Telegram credentiallari uchun `.env` asosiy manba hisoblanadi.

API ID/HASH, telefon, admin ID va welcome message qiymatlarini paneldagi POST endpointlari orqali ham saqlash mumkin.

## Telegram admin/configuration bot

Bu loyiha endi ikkita Telegram komponentdan iborat:

1. `bot.py` — UserBot. Mijozlardan kelgan private xabarlarni kuzatadi.
2. `admin_bot.py` — oddiy Telegram Bot API admin bot. API ID, API HASH, telefon, admin ID, monitoring va welcome message'ni Telegram ichidan sozlashga yordam beradi.

### Admin bot tokenini olish

BotFather orqali yangi bot yarating va tokenni `.env`ga yozing:

```env
ADMIN_BOT_TOKEN=123456:ABC...
ADMIN_USER_ID=123456789
```

`ADMIN_USER_ID` — konfiguratsiya botini boshqaradigan sizning Telegram ID'ingiz.

### Admin botni ishga tushirish

```bash
source .venv/bin/activate
python admin_bot.py
```

Botga `/start` yuboring.

Menyu:
- ⚙️ Telegram sozlamalari
- 💬 Avtojavob
- 📋 Guruhlar — UserBot topgan guruh/superguruhlarni tanlab xabar yuborish
- 📊 Holat
- 🆔 Mening ID
- 💾 Database — PostgreSQL jadvallarini bitta JSON fayl qilib yuboradi

Guruhlar `bot.py` ishga tushganda PostgreSQL `groups_` jadvaliga sinxronlanadi.
Admin bir nechta guruh tanlab, xabarni tasdiqlaydi; `admin_bot.py` topshiriqni
PostgreSQL navbatiga qo‘yadi, `bot.py` esa o‘zining mavjud Telethon session'i
orqali yuboradi va har bir guruh bo‘yicha natijani admin botga qaytaradi.
Tanlangan guruhlar adminning xotiradagi vaqtinchalik holati bo‘lib, bot qayta
ishga tushganda tozalanadi. Navbat jadvali `db.init_db()` tomonidan yaratiladi:

```sql
CREATE TABLE IF NOT EXISTS group_message_jobs (
    id BIGSERIAL PRIMARY KEY,
    requested_by BIGINT NOT NULL,
    group_telegram_ids BIGINT[] NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    results JSONB,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    notified BOOLEAN NOT NULL DEFAULT FALSE
);
```

API HASH maxfiy hisoblanadi va admin bot uni qayta ekranga chiqarib bermaydi.

### Xavfsizlik

API HASHni Telegram chatiga yuborish ham maxfiy ma'lumot uzatish hisoblanadi. Admin botga faqat o'zingizning Telegram ID'ingizga ruxsat bering va `ADMIN_BOT_TOKEN`, `.env`, `*.session` fayllarini GitHubga yubormang.


## Admin Bot — pure Python

`admin_bot.py` **aiogram ishlatmaydi**. Telegram Bot API bilan Python standard library (`urllib`) orqali ishlaydi.

Har bir bo'limga kirilganda faqat:

```text
⬅️ Orqaga
```

tugmasi chiqadi.

`⚙️ Telegram sozlamalari` bosilganda ketma-ket API ID → API HASH → telefon → admin ID → monitoring vaqti so'raladi.

`💬 Avtojavob` bosilganda faqat welcome message kiritish oynasi va `⬅️ Orqaga` tugmasi chiqadi.

Ishga tushirish:

```bash
source .venv/bin/activate
python admin_bot.py
```

Agar avvalgi `aiogram` xatosi chiqqan bo'lsa, endi `aiogram` kerak emas:

```bash
python -m pip install -r requirements.txt
```
