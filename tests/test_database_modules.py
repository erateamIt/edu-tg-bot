import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.database import (
    auto_reply,
    connection,
    customers,
    groups,
    messages,
    scheduled_messages,
    schema,
)
from app.telegram.customers import incoming_handler


class DatabaseModuleTests(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.connection = MagicMock()
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = self.cursor
        self.connection.cursor.return_value = cursor_context
        self.db_context = MagicMock()
        self.db_context.__enter__.return_value = self.connection

    def patch_db(self, module):
        return patch.object(module, "get_db", return_value=self.db_context)

    def test_schema_uses_postgresql_boolean_columns(self):
        with self.patch_db(schema):
            schema.init_db()
        ddl = "\n".join(call.args[0] for call in self.cursor.execute.call_args_list)
        self.assertIn("answered BOOLEAN NOT NULL DEFAULT FALSE", ddl)
        self.assertIn("auto_reply BOOLEAN NOT NULL DEFAULT FALSE", ddl)
        self.assertIn("enabled BOOLEAN NOT NULL DEFAULT FALSE", ddl)
        self.assertIn("enabled BOOLEAN NOT NULL DEFAULT TRUE", ddl)

    def test_add_message_passes_native_boolean_parameters(self):
        with self.patch_db(messages):
            messages.add_message(4, 25, "in", "Hello", "2026-10-08T09:00:00+00:00")

        sql, params = self.cursor.execute.call_args.args
        self.assertIn("answered,auto_reply", sql)
        self.assertIs(params[-2], False)
        self.assertIs(params[-1], False)

    def test_unanswered_queries_filter_incoming_unanswered_messages(self):
        with self.patch_db(messages):
            messages.get_unanswered()

        sql = self.cursor.execute.call_args.args[0]
        self.assertIn("m.direction='in' AND m.answered=FALSE", sql)
        self.assertIn("m2.direction='in' AND m2.answered=FALSE", sql)

    def test_group_enabled_parameter_is_python_bool(self):
        with self.patch_db(groups):
            groups.set_group_enabled(-100123, True)

        sql, params = self.cursor.execute.call_args.args
        self.assertIn("enabled=%s", sql)
        self.assertIs(params[0], True)

    def test_scheduled_claim_uses_sql_boolean(self):
        with self.patch_db(scheduled_messages):
            scheduled_messages.claim_due_scheduled("2026-10-08T09:00:00+00:00")

        sql = self.cursor.execute.call_args.args[0]
        self.assertIn("WHERE enabled=TRUE AND run_at<=%s", sql)

    def test_customer_creation_inserts_private_user_record(self):
        self.cursor.fetchone.side_effect = [None, {"id": 18}]
        with self.patch_db(customers):
            customer_id, is_new = customers.upsert_customer(
                9876,
                "student",
                "Student",
                None,
                None,
                "Hello",
                "2026-10-08T09:00:00+00:00",
            )

        self.assertEqual(customer_id, 18)
        self.assertTrue(is_new)
        sql, params = self.cursor.execute.call_args_list[-1].args
        self.assertIn("INSERT INTO customers", sql)
        self.assertEqual(params[0], 9876)

    def test_group_lookup_uses_telegram_id(self):
        with self.patch_db(groups):
            groups.get_group_by_telegram_id(-100123)

        self.cursor.execute.assert_called_once_with(
            "SELECT * FROM groups_ WHERE telegram_id=%s",
            (-100123,),
        )

    def test_scheduled_message_creation_sets_enabled_boolean(self):
        with self.patch_db(scheduled_messages):
            scheduled_messages.create_scheduled_message(
                7,
                "group",
                -100123,
                "Reminder",
                "2026-10-08T10:00:00+00:00",
            )

        sql, params = self.cursor.execute.call_args.args
        self.assertIn("VALUES(%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s)", sql)
        self.assertEqual(params[4], "group")

    def test_auto_reply_lookup_filters_enabled_rules(self):
        with self.patch_db(auto_reply):
            auto_reply.get_matching_auto_reply("course details")

        sql = self.cursor.execute.call_args.args[0]
        self.assertIn("WHERE enabled=TRUE", sql)

    def test_database_connection_commits_and_uses_configured_postgresql(self):
        fake_connection = MagicMock()
        with patch.object(connection.psycopg2, "connect", return_value=fake_connection) as connect:
            with connection.get_db() as opened_connection:
                self.assertIs(opened_connection, fake_connection)

        connect.assert_called_once()
        self.assertEqual(connect.call_args.kwargs["dbname"], connection.config.DB_NAME)
        self.assertEqual(connect.call_args.kwargs["host"], connection.config.DB_HOST)
        fake_connection.commit.assert_called_once()

    def test_customer_lookup_queries_postgresql_customer_id(self):
        with self.patch_db(customers):
            customers.get_customer_by_id(12)

        self.cursor.execute.assert_called_once_with(
            "SELECT * FROM customers WHERE id=%s",
            (12,),
        )


class TelegramPrivacyTests(unittest.TestCase):
    def test_non_private_message_returns_before_customer_processing(self):
        class NonPrivateEvent:
            is_private = False

            async def get_sender(self):
                raise AssertionError("Non-private events must return before sender lookup")

        with patch("app.telegram.customers.db.upsert_customer") as upsert_customer:
            asyncio.run(incoming_handler(NonPrivateEvent()))

        upsert_customer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
