"""User memberships in municipal units.

Revision ID: 0024_municipal_assignments
Revises: 0023_municipal_parties
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_municipal_assignments"
down_revision = "0023_municipal_parties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipal_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("municipal_units.id"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_id", "unit_id", name="uq_municipal_assignment"),
    )
    for column in ("tenant_id", "user_id", "unit_id"):
        op.create_index(f"ix_municipal_assignments_{column}", "municipal_assignments", [column])


def downgrade() -> None:
    for column in ("unit_id", "user_id", "tenant_id"):
        op.drop_index(f"ix_municipal_assignments_{column}", table_name="municipal_assignments")
    op.drop_table("municipal_assignments")
