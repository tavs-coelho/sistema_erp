"""Multi-tenancy: add subdomain to tenant_branding, tenant_id to users

Revision ID: 0006_multi_tenancy
Revises: 0005_iptu_parcelamento
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_multi_tenancy"
down_revision = "0005_iptu_parcelamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add subdomain slug to the tenant registry table
    op.add_column(
        "tenant_branding",
        sa.Column("subdomain", sa.String(80), nullable=True, unique=True),
    )
    op.create_index("ix_tenant_branding_subdomain", "tenant_branding", ["subdomain"])

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
    op.drop_index("ix_tenant_branding_subdomain", table_name="tenant_branding")
    op.drop_column("tenant_branding", "subdomain")
