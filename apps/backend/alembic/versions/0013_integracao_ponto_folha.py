"""Integração Ponto → Folha de Pagamento

Revision ID: 0013_integracao_ponto_folha
Revises: 0012_depreciacao_patrimonial
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_integracao_ponto_folha"
down_revision = "0012_depreciacao_patrimonial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Configuração de regras de integração por servidor
    op.create_table(
        "configuracoes_integracao_ponto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False, unique=True),
        sa.Column("desconto_falta_diaria", sa.Float(), nullable=True),
        sa.Column("percentual_hora_extra", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("desconto_atraso", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.create_index("ix_conf_integ_ponto_employee_id", "configuracoes_integracao_ponto", ["employee_id"])

    # Log de execuções da integração
    op.create_table(
        "integracao_ponto_folha_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("faltas_descontadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("horas_extras_creditadas", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("valor_desconto_faltas", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("valor_desconto_atrasos", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("valor_credito_horas_extras", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("executado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_integ_ponto_folha_logs_employee_id", "integracao_ponto_folha_logs", ["employee_id"])
    op.create_index("ix_integ_ponto_folha_logs_periodo", "integracao_ponto_folha_logs", ["periodo"])


def downgrade() -> None:
    op.drop_table("integracao_ponto_folha_logs")
    op.drop_table("configuracoes_integracao_ponto")
