"""Store optional signup details for product analytics."""

from alembic import op
import sqlalchemy as sa

revision = "0003_signup_events"
down_revision = "0002_api_key_modes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signup_events",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("key_id", sa.String(26), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("email", sa.Text()),
        sa.Column("use_case", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signup_events_key_id", "signup_events", ["key_id"])


def downgrade() -> None:
    op.drop_index("ix_signup_events_key_id", table_name="signup_events")
    op.drop_table("signup_events")
