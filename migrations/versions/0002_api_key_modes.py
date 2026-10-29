"""Add test/live mode and nullable rate limits to API keys."""

from alembic import op
import sqlalchemy as sa

revision = "0002_api_key_modes"
down_revision = "0001_v2_foundation"
branch_labels = None
depends_on = None


# batch_alter_table: SQLite can't ALTER COLUMN, so Alembic recreates the table there; on
# Postgres it emits plain ALTER statements.
def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.add_column(sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.alter_column("rate_limit_per_minute", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.alter_column("rate_limit_per_minute", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("is_test")
