"""add active columns and budget planning tables (PPA/LDO/LOA)

Revision ID: 0002_budget_planning
Revises: 0001_initial
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_budget_planning"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Colunas active em departments e users ─────────────────────────────────
    with op.batch_alter_table("departments") as batch_op:
        batch_op.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")))

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")))

    # ── PPA ───────────────────────────────────────────────────────────────────
    op.create_table(
        "ppas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_start", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "ppa_programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ppa_id", sa.Integer(), sa.ForeignKey("ppas.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False, server_default=""),
        sa.Column("estimated_amount", sa.Float(), nullable=False, server_default="0"),
    )

    # ── LDO ───────────────────────────────────────────────────────────────────
    op.create_table(
        "ldos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fiscal_year_id", sa.Integer(), sa.ForeignKey("fiscal_years.id"), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "ldo_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ldo_id", sa.Integer(), sa.ForeignKey("ldos.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(60), nullable=False, server_default="prioridade"),
    )

    # ── LOA ───────────────────────────────────────────────────────────────────
    op.create_table(
        "loas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fiscal_year_id", sa.Integer(), sa.ForeignKey("fiscal_years.id"), nullable=False),
        sa.Column("ldo_id", sa.Integer(), sa.ForeignKey("ldos.id"), nullable=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("total_revenue", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_expenditure", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "loa_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loa_id", sa.Integer(), sa.ForeignKey("loas.id"), nullable=False),
        sa.Column("function_code", sa.String(10), nullable=False),
        sa.Column("subfunction_code", sa.String(10), nullable=False),
        sa.Column("program_code", sa.String(20), nullable=False),
        sa.Column("action_code", sa.String(20), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(30), nullable=False, server_default="despesa"),
        sa.Column("authorized_amount", sa.Float(), nullable=False),
        sa.Column("executed_amount", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("loa_items")
    op.drop_table("loas")
    op.drop_table("ldo_goals")
    op.drop_table("ldos")
    op.drop_table("ppa_programs")
    op.drop_table("ppas")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("active")

    with op.batch_alter_table("departments") as batch_op:
        batch_op.drop_column("active")
