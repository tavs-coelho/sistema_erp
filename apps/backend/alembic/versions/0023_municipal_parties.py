"""Municipal parties and supplier contacts.

Revision ID: 0023_municipal_parties
Revises: 0022_municipal_units
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_municipal_parties"
down_revision = "0022_municipal_units"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipal_parties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("document", sa.String(14), nullable=True),
        sa.Column("email", sa.String(180), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "document", name="uq_municipal_parties_document"),
        sa.CheckConstraint("kind IN ('pessoa', 'fornecedor')", name="ck_municipal_parties_kind"),
    )
    op.create_index("ix_municipal_parties_tenant_id", "municipal_parties", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_municipal_parties_tenant_id", table_name="municipal_parties")
    op.drop_table("municipal_parties")
