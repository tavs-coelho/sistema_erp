"""0018_tenant_branding — white-label settings table

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-20

Changes:
  - CREATE TABLE tenant_branding  (single-row white-label config)
"""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_branding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_name", sa.String(120), nullable=False, server_default="Prefeitura Municipal"),
        sa.Column("logo_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("primary_color", sa.String(9), nullable=False, server_default="#1d4ed8"),
        sa.Column("secondary_color", sa.String(9), nullable=False, server_default="#0f172a"),
        sa.Column("accent_color", sa.String(9), nullable=False, server_default="#0ea5e9"),
        sa.Column("favicon_url", sa.String(500), nullable=False, server_default="/favicon.ico"),
        sa.Column("app_title", sa.String(200), nullable=False, server_default="Sistema ERP Municipal"),
        sa.Column("subdomain", sa.String(80), nullable=True, unique=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_tenant_branding_subdomain", "tenant_branding", ["subdomain"])
    # Insert the default row so GET /branding always returns a result without
    # requiring a migration-time upsert from application code.
    op.execute(
        "INSERT INTO tenant_branding (id, org_name, logo_url, primary_color, secondary_color, accent_color, favicon_url, app_title, updated_at) "
        "VALUES (1, 'Prefeitura Municipal', '', '#1d4ed8', '#0f172a', '#0ea5e9', '/favicon.ico', 'Sistema ERP Municipal', CURRENT_TIMESTAMP)"
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_branding_subdomain", table_name="tenant_branding")
    op.drop_table("tenant_branding")
