"""Multi-tenancy: add tenant_id to users

Revision ID: 0006_multi_tenancy
Revises: 0018
Create Date: 2026-04-20

Note: the tenant_branding table (including the subdomain column) is created by
revision 0018_tenant_branding which this migration must follow.
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_multi_tenancy"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Scope each user to a tenant (NULL → default tenant id=1)
    op.add_column(
        "users",
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenant_branding.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")
