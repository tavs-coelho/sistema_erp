"""Municipal administrative units.

Revision ID: 0022_municipal_units
Revises: 0021_tenant_core
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_municipal_units"
down_revision = "0021_tenant_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipal_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("address", sa.String(350), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_municipal_units_tenant_code"),
    )
    op.create_index("ix_municipal_units_tenant_id", "municipal_units", ["tenant_id"])
    op.create_index("ix_municipal_units_department_id", "municipal_units", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_municipal_units_department_id", table_name="municipal_units")
    op.drop_index("ix_municipal_units_tenant_id", table_name="municipal_units")
    op.drop_table("municipal_units")
