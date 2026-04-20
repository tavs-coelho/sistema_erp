"""Protocolo/processos administrativos e convênios

Revision ID: 0003_protocolo_convenios
Revises: 0002_budget_planning
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_protocolo_convenios"
down_revision = "0002_budget_planning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Protocolo ─────────────────────────────────────────────────────────────
    op.create_table(
        "protocolos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.String(40), nullable=False, unique=True),
        sa.Column("tipo", sa.String(60), nullable=False),
        sa.Column("assunto", sa.String(255), nullable=False),
        sa.Column("interessado", sa.String(160), nullable=False),
        sa.Column("interessado_doc", sa.String(20), nullable=True),
        sa.Column("origem_department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("destino_department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="protocolado"),
        sa.Column("prioridade", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("data_entrada", sa.Date(), nullable=False),
        sa.Column("prazo", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_protocolos_numero", "protocolos", ["numero"], unique=True)

    op.create_table(
        "tramitacoes_protocolo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("protocolo_id", sa.Integer(), sa.ForeignKey("protocolos.id"), nullable=False),
        sa.Column("de_department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("para_department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("acao", sa.String(60), nullable=False),
        sa.Column("despacho", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── Convênios ─────────────────────────────────────────────────────────────
    op.create_table(
        "convenios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.String(40), nullable=False, unique=True),
        sa.Column("objeto", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False, server_default="recebimento"),
        sa.Column("concedente", sa.String(160), nullable=False),
        sa.Column("cnpj_concedente", sa.String(18), nullable=True),
        sa.Column("valor_total", sa.Float(), nullable=False),
        sa.Column("contrapartida", sa.Float(), nullable=False, server_default="0"),
        sa.Column("data_assinatura", sa.Date(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="vigente"),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("loa_item_id", sa.Integer(), sa.ForeignKey("loa_items.id"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_convenios_numero", "convenios", ["numero"], unique=True)

    op.create_table(
        "convenio_desembolsos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("convenio_id", sa.Integer(), sa.ForeignKey("convenios.id"), nullable=False),
        sa.Column("numero_parcela", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("data_prevista", sa.Date(), nullable=False),
        sa.Column("data_efetiva", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="previsto"),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("convenio_desembolsos")
    op.drop_index("ix_convenios_numero", table_name="convenios")
    op.drop_table("convenios")
    op.drop_table("tramitacoes_protocolo")
    op.drop_index("ix_protocolos_numero", table_name="protocolos")
    op.drop_table("protocolos")
