"""Municipal protocol task tracking.

Revision ID: 0026_municipal_tasks
Revises: 0025_municipal_documents
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_municipal_tasks"
down_revision = "0025_municipal_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipal_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("protocol_id", sa.Integer(), sa.ForeignKey("protocolos.id"), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("assigned_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(24), nullable=False, server_default="aberta"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("priority IN ('normal','alta','urgente')", name="ck_municipal_tasks_priority"),
        sa.CheckConstraint("status IN ('aberta','em_andamento','concluida','cancelada')", name="ck_municipal_tasks_status"),
    )
    for col in ("tenant_id", "protocol_id", "assigned_user_id"):
        op.create_index(f"ix_municipal_tasks_{col}", "municipal_tasks", [col])


def downgrade() -> None:
    for col in ("assigned_user_id", "protocol_id", "tenant_id"):
        op.drop_index(f"ix_municipal_tasks_{col}", table_name="municipal_tasks")
    op.drop_table("municipal_tasks")
