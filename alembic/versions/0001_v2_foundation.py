"""v2 foundation: api_keys, datasets, analyses, webhooks, webhook_deliveries, audit_log

Revision ID: 0001_v2_foundation
Revises:
Create Date: 2026-05-12

Tables follow docs/api/SPEC_v2.md §3 with eng-review adjustments:
  - analyses has unique(key_id, idempotency_key) for Postgres-backed idempotency (A2)
  - webhooks stores signing_secret_ciphertext, not hash (A1)
  - analyses has last_progress_at for janitor heartbeat (T2)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_v2_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_dataset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_analysis_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_succeeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("touchpoints_processed", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    op.create_table(
        "datasets",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("key_id", sa.String(32), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("filename", sa.String(512), nullable=True),
        sa.Column("storage_uri", sa.String(1024), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("touchpoint_count", sa.Integer(), nullable=True),
        sa.Column("unique_customers", sa.Integer(), nullable=True),
        sa.Column("schema_fingerprint", sa.String(128), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),  # validating | ready | invalid
        sa.Column("validation_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_datasets_key_id", "datasets", ["key_id"])
    op.create_index("ix_datasets_status", "datasets", ["status"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("key_id", sa.String(32), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", sa.String(32), sa.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("models", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),  # queued | running | succeeded | failed | canceled
        sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("comparison", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("last_progress_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_id", sa.String(32), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("key_id", "idempotency_key", name="uq_analyses_key_idempotency"),
    )
    op.create_index("ix_analyses_key_id", "analyses", ["key_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_index("ix_analyses_dataset_id", "analyses", ["dataset_id"])

    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("key_id", sa.String(32), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("signing_secret_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("signing_secret_prefix", sa.String(16), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhooks_key_id", "webhooks", ["key_id"])

    op.create_foreign_key(
        "fk_analyses_webhook_id",
        "analyses", "webhooks",
        ["webhook_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("webhook_id", sa.String(32), sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index("ix_webhook_deliveries_next_retry", "webhook_deliveries", ["next_retry_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("key_id", sa.String(32), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(32), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_key_id", "audit_log", ["key_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("webhook_deliveries")
    op.drop_constraint("fk_analyses_webhook_id", "analyses", type_="foreignkey")
    op.drop_table("webhooks")
    op.drop_table("analyses")
    op.drop_table("datasets")
    op.drop_table("api_keys")
