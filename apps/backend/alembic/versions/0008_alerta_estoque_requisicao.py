"""Alerta de Estoque Mínimo + Requisição de Compra

Revision ID: 0008_alerta_estoque_requisicao
Revises: 0007_integracao_compras_almoxarifado
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_alerta_estoque_requisicao"
down_revision = "0007_integracao_compras_almoxarifado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Alertas de Estoque Mínimo ──────────────────────────────────────────────
    op.create_table(
        "alertas_estoque_minimo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("itens_almoxarifado.id"), nullable=False),
        sa.Column("movimentacao_id", sa.Integer(), sa.ForeignKey("movimentacoes_estoque.id"), nullable=True),
        sa.Column("saldo_no_momento", sa.Float(), nullable=False),
        sa.Column("estoque_minimo", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberto"),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolvido_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alertas_estoque_minimo_item_id", "alertas_estoque_minimo", ["item_id"])

    # ── Requisições de Compra ──────────────────────────────────────────────────
    op.create_table(
        "requisicoes_compra",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("itens_almoxarifado.id"), nullable=False),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("alerta_id", sa.Integer(), sa.ForeignKey("alertas_estoque_minimo.id"), nullable=True),
        sa.Column("processo_id", sa.Integer(), sa.ForeignKey("procurement_processes.id"), nullable=True),
        sa.Column("quantidade_sugerida", sa.Float(), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("solicitante_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_requisicoes_compra_item_id", "requisicoes_compra", ["item_id"])
    op.create_index("ix_requisicoes_compra_status", "requisicoes_compra", ["status"])


def downgrade() -> None:
    op.drop_table("requisicoes_compra")
    op.drop_table("alertas_estoque_minimo")
