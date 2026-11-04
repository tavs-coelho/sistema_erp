"""Notifications, support requests and replies.

Revision ID: 0027_nucleo_support
Revises: 0026_municipal_tasks
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_nucleo_support"
down_revision = "0026_municipal_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipal_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="sistema"),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("reference_type", sa.String(32), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "municipal_support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberto"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("priority IN ('normal','alta','critica')", name="ck_municipal_ticket_priority"),
        sa.CheckConstraint("status IN ('aberto','em_atendimento','resolvido','fechado')", name="ck_municipal_ticket_status"),
    )
    op.create_table(
        "municipal_support_replies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("municipal_support_tickets.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for name, columns in {
        "municipal_notices": ("tenant_id", "user_id"),
        "municipal_support_tickets": ("tenant_id", "created_by"),
        "municipal_support_replies": ("tenant_id", "ticket_id"),
    }.items():
        for column in columns:
            op.create_index(f"ix_{name}_{column}", name, [column])


def downgrade() -> None:
    for name, columns in (
        ("municipal_support_replies", ("ticket_id", "tenant_id")),
        ("municipal_support_tickets", ("created_by", "tenant_id")),
        ("municipal_notices", ("user_id", "tenant_id")),
    ):
        for column in columns:
            op.drop_index(f"ix_{name}_{column}", table_name=name)
        op.drop_table(name)
