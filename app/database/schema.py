"""PostgreSQL schema initialization."""
from datetime import datetime, timezone

from .connection import get_db


def init_db():
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id BIGSERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                lead_status TEXT NOT NULL DEFAULT 'new',
                status_source TEXT NOT NULL DEFAULT 'manual',
                first_message TEXT,
                last_message TEXT,
                last_message_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                customer_id BIGINT NOT NULL REFERENCES customers(id),
                telegram_message_id BIGINT,
                direction TEXT NOT NULL,
                text TEXT,
                sent_at TEXT NOT NULL,
                answered BOOLEAN NOT NULL DEFAULT FALSE,
                auto_reply BOOLEAN NOT NULL DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS groups_ (
                id BIGSERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                username TEXT,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id BIGSERIAL PRIMARY KEY,
                group_telegram_id BIGINT,
                text TEXT NOT NULL,
                run_at TEXT NOT NULL,
                repeat TEXT NOT NULL DEFAULT 'once',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                last_run_at TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

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

            CREATE TABLE IF NOT EXISTS tags (
                id BIGSERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customer_tags (
                customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                tag_id BIGINT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                source TEXT NOT NULL DEFAULT 'manual',
                confidence NUMERIC(4,2) DEFAULT 1.00,
                created_at TEXT NOT NULL,
                PRIMARY KEY(customer_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS auto_reply_rules (
                id BIGSERIAL PRIMARY KEY,
                keyword TEXT UNIQUE NOT NULL,
                response TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outgoing_messages (
                id BIGSERIAL PRIMARY KEY,
                requested_by BIGINT NOT NULL,
                recipient_type TEXT NOT NULL CHECK (recipient_type IN ('user', 'group')),
                recipient_id BIGINT NOT NULL,
                message_type TEXT NOT NULL DEFAULT 'text',
                text TEXT,
                media_path TEXT,
                caption TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT,
                created_at TEXT NOT NULL,
                sent_at TEXT
            );

            CREATE TABLE IF NOT EXISTS logs (
                id BIGSERIAL PRIMARY KEY,
                admin_user_id BIGINT,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                details JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TEXT NOT NULL
            );

            ALTER TABLE customers
                ADD COLUMN IF NOT EXISTS status_source TEXT NOT NULL DEFAULT 'manual';
            ALTER TABLE scheduled_messages
                ALTER COLUMN group_telegram_id DROP NOT NULL;
            ALTER TABLE scheduled_messages
                ADD COLUMN IF NOT EXISTS recipient_type TEXT NOT NULL DEFAULT 'group';
            ALTER TABLE scheduled_messages
                ADD COLUMN IF NOT EXISTS recipient_id BIGINT;
            ALTER TABLE scheduled_messages
                ADD COLUMN IF NOT EXISTS message_type TEXT NOT NULL DEFAULT 'text';
            ALTER TABLE scheduled_messages
                ADD COLUMN IF NOT EXISTS media_path TEXT;
            ALTER TABLE scheduled_messages
                ADD COLUMN IF NOT EXISTS caption TEXT;
            ALTER TABLE tags
                ADD COLUMN IF NOT EXISTS slug TEXT;
            ALTER TABLE tags
                ADD COLUMN IF NOT EXISTS description TEXT;
            ALTER TABLE customer_tags
                ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';
            ALTER TABLE customer_tags
                ADD COLUMN IF NOT EXISTS confidence NUMERIC(4,2) DEFAULT 1.00;

            UPDATE scheduled_messages
            SET recipient_id=group_telegram_id
            WHERE recipient_id IS NULL AND group_telegram_id IS NOT NULL;

            UPDATE tags
            SET slug=LOWER(REPLACE(REPLACE(name, ' ', '_'), '-', '_'))
            WHERE slug IS NULL OR slug = '';

            CREATE INDEX IF NOT EXISTS idx_messages_customer ON messages(customer_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
            CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
            CREATE INDEX IF NOT EXISTS idx_group_message_jobs_pending
                ON group_message_jobs(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_outgoing_messages_pending
                ON outgoing_messages(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_due
                ON scheduled_messages(enabled, run_at);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_slug ON tags(slug) WHERE slug IS NOT NULL;
            """)
            cur.execute(
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS "
                "lead_status TEXT NOT NULL DEFAULT 'new'"
            )

            defaults = {
                "welcome_message": """Assalomu alaykum! 👋

O‘quv markazimizga xush kelibsiz.

📚 Kurslar:
• Ingliz tili
• IELTS
• Rus tili
• Matematika
• Python
• Frontend / Backend

💰 Kurs narxlari: 350 000 so‘mdan.
🕐 Darslar: 09:00–20:00
📍 Manzil: Samarqand shahri

Batafsil ma’lumot uchun kurs nomini yozing.""",
                "monitor_minutes": "5",
                "auto_reply_enabled": "true",
                "auto_tag_enabled": "true",
                "auto_tag_min_confidence": "0.70",
                "auto_tag_ai_enabled": "false",
                "report_time": "21:00",
                "report_timezone": "Asia/Tashkent",
            }
            for key, value in defaults.items():
                cur.execute(
                    "INSERT INTO settings(key,value) VALUES(%s,%s) "
                    "ON CONFLICT(key) DO NOTHING",
                    (key, value),
                )

            default_tags = [
                ("🐍 Python", "python", "Python course interest"),
                ("💻 Backend", "backend", "Backend development interest"),
                ("🌐 Frontend", "frontend", "Frontend development interest"),
                ("🇬🇧 IELTS", "ielts", "IELTS course interest"),
                ("📚 English", "english", "English course interest"),
                ("💰 Price", "price", "Pricing questions"),
                ("📍 Location", "location", "Location questions"),
                ("📅 Course Date", "course_date", "Course start date questions"),
                ("🔥 Interested", "interested", "Customer expresses interest"),
                ("🟢 Registered", "registered", "Customer already registered"),
                ("🔴 Not Interested", "not_interested", "Customer not interested"),
                ("❓ General Question", "general", "General question"),
            ]
            for name, slug, description in default_tags:
                cur.execute(
                    "INSERT INTO tags(name, slug, description, created_at) VALUES(%s,%s,%s,%s) "
                    "ON CONFLICT(name) DO NOTHING",
                    (name, slug, description, datetime.now(timezone.utc).isoformat()),
                )
