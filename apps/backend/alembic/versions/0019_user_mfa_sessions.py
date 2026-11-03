"""Encrypted MFA state, one-time recovery codes and revocable JWT session version.

Revision ID: 0019_user_mfa_sessions
Revises: 0006_multi_tenancy
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_user_mfa_sessions"
down_revision = "0006_multi_tenancy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "user_mfa",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("encrypted_secret", sa.String(512), nullable=True),
        sa.Column("encrypted_pending_secret", sa.String(512), nullable=True),
        sa.Column("pending_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_used_counter", sa.Integer(), nullable=False, server_default="-1"),
    )
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_mfa_recovery_codes_user_id", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_table("user_mfa")
    op.drop_column("users", "session_version")
