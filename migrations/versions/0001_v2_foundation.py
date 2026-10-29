"""Create the v2 foundation resource tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_v2_foundation"
down_revision = None
branch_labels = None
depends_on = None

json_value = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
dataset_status = sa.Enum("validating", "ready", "invalid", name="dataset_status")
analysis_status = sa.Enum(
    "queued", "running", "succeeded", "failed", "cancelled", name="analysis_status"
)


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scopes", json_value, nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "datasets",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("key_id", sa.String(26), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("touchpoint_count", sa.Integer()),
        sa.Column("unique_customers", sa.Integer()),
        sa.Column("schema_fingerprint", sa.String(128)),
        sa.Column("status", dataset_status, nullable=False),
        sa.Column("validation_report", json_value),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_datasets_key_id", "datasets", ["key_id"])

    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("key_id", sa.String(26), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("events", json_value, nullable=False),
        sa.Column("signing_secret_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("signing_secret_prefix", sa.String(8), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_webhooks_key_id", "webhooks", ["key_id"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("key_id", sa.String(26), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("dataset_id", sa.String(26), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("models", json_value, nullable=False),
        sa.Column("options", json_value),
        sa.Column("status", analysis_status, nullable=False),
        sa.Column("progress", json_value),
        sa.Column("results", json_value),
        sa.Column("comparison", json_value),
        sa.Column("idempotency_key", sa.Text()),
        sa.Column("last_progress_at", sa.DateTime(timezone=True)),
        sa.Column("webhook_id", sa.String(26), sa.ForeignKey("webhooks.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", json_value),
    )
    op.create_index("ix_analyses_key_id", "analyses", ["key_id"])
    op.create_index("ix_analyses_dataset_id", "analyses", ["dataset_id"])
    op.create_index(
        "uq_analyses_key_id_idempotency_key",
        "analyses",
        ["key_id", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("webhook_id", sa.String(26), sa.ForeignKey("webhooks.id"), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", json_value, nullable=False),
        sa.Column("response_code", sa.Integer()),
        sa.Column("response_body", sa.Text()),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("key_id", sa.String(26), sa.ForeignKey("api_keys.id")),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("request_id", sa.String(64)),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_log_key_id", "audit_log", ["key_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_key_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index("uq_analyses_key_id_idempotency_key", table_name="analyses")
    op.drop_index("ix_analyses_dataset_id", table_name="analyses")
    op.drop_index("ix_analyses_key_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_webhooks_key_id", table_name="webhooks")
    op.drop_table("webhooks")
    op.drop_index("ix_datasets_key_id", table_name="datasets")
    op.drop_table("datasets")
    op.drop_table("api_keys")
