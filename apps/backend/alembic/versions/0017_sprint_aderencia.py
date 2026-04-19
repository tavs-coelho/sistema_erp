"""0017_sprint_aderencia — rate limiting setup, loa_item_id em commitments, escalas_ferias

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-19

Changes:
  - ADD COLUMN commitments.loa_item_id (FK → loa_items)
  - CREATE TABLE escalas_ferias
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ORC-05: loa_item_id em commitments para atualização automática do saldo executado
    op.add_column(
        "commitments",
        sa.Column("loa_item_id", sa.Integer(), sa.ForeignKey("loa_items.id"), nullable=True),
    )
    op.create_index("ix_commitments_loa_item_id", "commitments", ["loa_item_id"])

    # RH-07: tabela de escala de férias
    op.create_table(
        "escalas_ferias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("ano_referencia", sa.Integer(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("dias_gozados", sa.Integer(), nullable=False),
        sa.Column("fracao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="programada"),
        sa.Column("aprovado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_escalas_ferias_employee_id", "escalas_ferias", ["employee_id"])
    op.create_index("ix_escalas_ferias_ano_referencia", "escalas_ferias", ["ano_referencia"])
    op.create_index("ix_escalas_ferias_status", "escalas_ferias", ["status"])
    op.create_index("ix_escalas_ferias_data_inicio", "escalas_ferias", ["data_inicio"])


def downgrade() -> None:
    op.drop_table("escalas_ferias")
    op.drop_index("ix_commitments_loa_item_id", table_name="commitments")
    op.drop_column("commitments", "loa_item_id")
