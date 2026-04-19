"""Recálculo automático do Payslip — log de recalculates

Revision ID: 0014_recalculo_payslip
Revises: 0013_integracao_ponto_folha
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_recalculo_payslip"
down_revision = "0013_integracao_ponto_folha"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recalcular_payslip_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("gross_amount_anterior", sa.Float(), nullable=True),
        sa.Column("gross_amount_novo", sa.Float(), nullable=False),
        sa.Column("deductions_anterior", sa.Float(), nullable=True),
        sa.Column("deductions_novo", sa.Float(), nullable=False),
        sa.Column("net_amount_anterior", sa.Float(), nullable=True),
        sa.Column("net_amount_novo", sa.Float(), nullable=False),
        sa.Column("origem", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("executado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recalc_payslip_logs_employee_id", "recalcular_payslip_logs", ["employee_id"])
    op.create_index("ix_recalc_payslip_logs_periodo", "recalcular_payslip_logs", ["periodo"])


def downgrade() -> None:
    op.drop_table("recalcular_payslip_logs")
