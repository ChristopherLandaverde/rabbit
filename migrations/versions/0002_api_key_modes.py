"""Add test/live mode and nullable rate limits to API keys."""

from alembic import op
import sqlalchemy as sa

revision = "0002_api_key_modes"
down_revision = "0001_v2_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("api_keys", "rate_limit_per_minute", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("api_keys", "rate_limit_per_minute", existing_type=sa.Integer(), nullable=False)
    op.drop_column("api_keys", "is_test")
