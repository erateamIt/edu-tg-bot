# Education Telegram UserBot

Telegram CRM built with Python, Telethon, Telegram Bot API, PostgreSQL and
FastAPI. PostgreSQL (`psycopg2`) is the only application database. The
UserBot captures customers only when they initiate a private chat; group and
supergroup discovery is stored separately.

## Project layout

```text
app/
  admin/       Telegram Bot API admin interface and feature workflows
  core/        Environment configuration, constants and logging setup
  database/    PostgreSQL schema and domain data access modules
  panel/       FastAPI app, HTTP routes and environment services
  scheduler/   PostgreSQL scheduled-message worker and daily reports
  telegram/    Shared Telethon client, QR login, handlers and workers
  utils/       Datetime and project data-file helpers
data/
  backups/     Generated database backup JSON
  exports/     Generated database export JSON
logs/          Application log files
scripts/       Database initialization and backup commands
tests/         Unit tests using mocked PostgreSQL connections

run.py         UserBot entry point
run_admin.py   Admin Bot entry point
run_panel.py   FastAPI panel entry point
```

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `API_ID` and `API_HASH` using the credentials from
[my.telegram.org](https://my.telegram.org). Fill in PostgreSQL connection
settings and `ADMIN_BOT_TOKEN` in `.env`. Keep `.env` and the Telethon session
private; neither belongs in source control or a shared backup.

## PostgreSQL setup

Create a PostgreSQL role and database (replace the password with a strong
private value):

```bash
sudo -u postgres psql
```

```sql
CREATE USER education_user WITH PASSWORD 'CHANGE_THIS_PRIVATE_PASSWORD';
CREATE DATABASE education_center OWNER education_user;
\q
```

Set these values in `.env`:

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=education_center
DB_USER=education_user
DB_PASSWORD=CHANGE_THIS_PRIVATE_PASSWORD
```

Initialize tables explicitly, or let any application entry point initialize
them on startup:

```bash
python -m scripts.init_database
```

The schema uses PostgreSQL `BOOLEAN` columns for message state and enabled
flags. Verify those types with:

```bash
psql -d education_center -c "
SELECT table_name, column_name, data_type, column_default
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

Every listed `data_type` should be `boolean`.

To recreate the database from scratch, stop all project processes first.
**The following deletes all data in the named database.** Back up any data
that must be retained:

```bash
sudo -u postgres dropdb --if-exists education_center
sudo -u postgres createdb --owner=education_user education_center
python -m scripts.init_database
```

## Run the services

Start the UserBot:

```bash
python run.py
```

On first login, scan the displayed QR code in Telegram at
**Settings → Devices → Link Desktop Device**. The existing
`education_center.session` session name is preserved.

Start the Telegram Bot API Admin Bot in a separate terminal:

```bash
python run_admin.py
```

Start the FastAPI panel in another terminal:

```bash
python run_panel.py
```

The panel defaults to `http://127.0.0.1:8000`. Sign in to the Uzbek-language
dashboard with `PANEL_TOKEN` from `.env`; the panel keeps the login in an
HttpOnly session cookie. API requests can continue to authenticate with the
`X-Panel-Token` header.

The Admin Bot uses Telegram Bot API only. It puts send requests in PostgreSQL;
the one running UserBot process delivers them through its shared Telethon
client. Do not start another Telethon client for the Admin Bot.

## Configuration

Important `.env` settings:

- `API_ID`, `API_HASH`, `PHONE_NUMBER`: Telegram UserBot credentials.
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL.
- `ADMIN_BOT_TOKEN`: Telegram Bot API token.
- `ADMIN_USER_ID`: Admin Bot allowlist; `0` retains the existing allow-all
  behavior and should not be used in production.
- `ADMIN_CHAT_ID`, `MONITOR_MINUTES`: unanswered-message notifications.
- `REPORT_USER_ID`, `REPORT_TIME`, `REPORT_TIMEZONE`: daily report delivery.
- `BACKUP_USER_ID`: optional backup recipient.
- `SESSION_NAME`: defaults to `education_center`.
- `PANEL_HOST`, `PANEL_PORT`, `PANEL_TOKEN`: web panel.

Group selection in the Admin Bot is temporary per-admin state. Discovered
groups and queued messages persist in PostgreSQL. Customers are created only
from incoming private messages; groups are never stored in `customers`.

## Backups and logs

The Admin Bot's JSON export is written under `data/exports/`; its backup
action and the CLI backup command write under `data/backups/`. Export output
filters setting keys that appear secret-bearing; it does not include `.env`
or Telethon session files. Review generated backups as sensitive CRM data.

Run a backup manually:

```bash
python -m scripts.backup_database
```

Application logs are written under `logs/`.

## Tests

Tests mock the PostgreSQL connection and do not require a live Telegram login
or PostgreSQL server:

```bash
python -m unittest discover -v
python -m compileall app scripts tests
```

## Troubleshooting

- **Missing configuration:** confirm `.env` exists at the project root and
  contains `API_ID`, `API_HASH`, `DB_PASSWORD`, and `ADMIN_BOT_TOKEN`.
- **PostgreSQL connection error:** verify the PostgreSQL service, database
  role/password, and `DB_*` settings.
- **No groups listed:** start the UserBot and wait for dialog synchronization;
  only groups and supergroups are registered.
- **Admin send remains queued:** keep `run.py` running; that process owns the
  Telethon session and drains PostgreSQL send queues.
- **Panel login reports a configuration error:** set a non-empty `PANEL_TOKEN`
  in the project-root `.env` file, then restart `run_panel.py`.
- **Panel API authentication fails:** pass the configured `PANEL_TOKEN` in the
  `X-Panel-Token` header.
