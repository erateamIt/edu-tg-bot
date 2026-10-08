"""Eski data.sqlite3 faylini PostgreSQL bazasiga bir martalik ko'chirish."""
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

import db

load_dotenv(override=True)
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", "data.sqlite3"))


def main():
    if not SQLITE_PATH.exists():
        raise SystemExit(f"SQLite fayl topilmadi: {SQLITE_PATH}")

    print("PostgreSQL jadvallari yaratilmoqda...")
    db.init_db()

    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    try:
        # settings
        for row in con.execute("SELECT key, value FROM settings"):
            db.set_setting(row["key"], row["value"])

        # customers + messages
        customer_map = {}
        for row in con.execute("SELECT * FROM customers ORDER BY id"):
            customer_id, _ = db.upsert_customer(
                row["telegram_id"], row["username"], row["first_name"], row["last_name"],
                row["phone"], row["last_message"], row["last_message_at"] or row["updated_at"]
            )
            customer_map[row["id"]] = customer_id
            db.set_customer_status(customer_id, row["status"])

        for row in con.execute("SELECT * FROM messages ORDER BY id"):
            new_customer_id = customer_map.get(row["customer_id"])
            if new_customer_id:
                db.add_message(
                    new_customer_id, row["telegram_message_id"], row["direction"],
                    row["text"], row["sent_at"], bool(row["answered"]),
                    bool(row["auto_reply"])
                )

        # groups
        for row in con.execute("SELECT * FROM groups_ ORDER BY id"):
            db.sync_group(row["telegram_id"], row["title"], row["username"])
            db.set_group_enabled(row["telegram_id"], bool(row["enabled"]))

        # scheduled messages
        for row in con.execute("SELECT * FROM scheduled_messages ORDER BY id"):
            new_id = db.add_scheduled(row["group_telegram_id"], row["text"], row["run_at"], row["repeat"])
            if not row["enabled"]:
                db.disable_scheduled(new_id)
            if row["last_run_at"]:
                db.mark_scheduled_run(new_id, row["last_run_at"])

    finally:
        con.close()

    print("✅ SQLite → PostgreSQL migratsiya tugadi.")
    print("Endi data.sqlite3 faylini o'chirmang; avval botni tekshirib oling.")


if __name__ == "__main__":
    main()
