"""Per-key cap on in-flight analyses (#18, A4)."""

from alembic import op
import sqlalchemy as sa

revision = "0004_analysis_concurrency_cap"
down_revision = "0003_signup_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.add_column(
            sa.Column("max_concurrent_analyses", sa.Integer(), nullable=False, server_default="3")
        )


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.drop_column("max_concurrent_analyses")
