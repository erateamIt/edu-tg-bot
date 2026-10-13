"""Public PostgreSQL data-access API and domain modules."""
from .schema import init_db
from .settings import get_setting, set_setting
from .customers import (
    count_customers,
    count_new_customers,
    get_customer,
    get_customer_by_id,
    get_customer_by_telegram_id,
    list_customers,
    list_customers_page,
    set_customer_status,
    upsert_customer,
)
from .messages import (
    add_message,
    count_unanswered,
    get_unanswered,
    get_unanswered_page,
    list_messages,
    mark_customer_overdue,
    mark_customer_waiting,
    record_customer_reply,
)
from .groups import (
    get_group_by_telegram_id,
    get_groups,
    list_groups,
    set_group_enabled,
    sync_group,
)
from .scheduled_messages import (
    add_scheduled,
    advance_scheduled_message,
    claim_due_scheduled,
    create_scheduled_message,
    list_scheduled,
)
from .auto_reply import (
    add_auto_reply_rule,
    delete_auto_reply_rule,
    get_matching_auto_reply,
    list_auto_reply_rules,
    set_auto_reply_rule_enabled,
)
from .tags import (
    add_customer_tag,
    ensure_tag,
    get_tag_by_slug,
    list_customer_tags,
    list_tags,
    remove_customer_tag,
)
from .logs import add_log, list_logs_page
from .reports import claim_daily_report, get_daily_stats
from .jobs import (
    claim_group_message_job,
    claim_outgoing_message,
    complete_group_message_job,
    enqueue_group_message,
    enqueue_outgoing_message,
    finish_outgoing_message,
    get_unnotified_group_message_jobs,
    mark_group_message_job_notified,
)
from .backups import database_info, export_database

__all__ = [
    "init_db", "get_setting", "set_setting",
    "count_customers", "count_new_customers", "get_customer",
    "get_customer_by_id", "get_customer_by_telegram_id", "list_customers",
    "list_customers_page", "set_customer_status", "upsert_customer",
    "add_message", "count_unanswered", "get_unanswered",
    "get_unanswered_page", "list_messages", "mark_customer_overdue",
    "mark_customer_waiting", "record_customer_reply", "get_group_by_telegram_id", "get_groups", "list_groups",
    "set_group_enabled", "sync_group", "add_scheduled",
    "advance_scheduled_message", "claim_due_scheduled",
    "create_scheduled_message", "list_scheduled", "add_auto_reply_rule", "delete_auto_reply_rule",
    "get_matching_auto_reply", "list_auto_reply_rules",
    "set_auto_reply_rule_enabled", "add_customer_tag", "ensure_tag",
    "get_tag_by_slug", "list_tags", "list_customer_tags", "remove_customer_tag",
    "add_log", "list_logs_page",
    "claim_daily_report", "get_daily_stats", "claim_group_message_job",
    "claim_outgoing_message", "complete_group_message_job",
    "enqueue_group_message", "enqueue_outgoing_message",
    "finish_outgoing_message", "get_unnotified_group_message_jobs",
    "mark_group_message_job_notified", "database_info", "export_database",
    ]
