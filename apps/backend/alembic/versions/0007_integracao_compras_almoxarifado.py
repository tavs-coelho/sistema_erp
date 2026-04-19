"""Integração Almoxarifado ↔ Compras

Revision ID: 0007_integracao_compras_almoxarifado
Revises: 0006_almoxarifado
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_integracao_compras_almoxarifado"
down_revision = "0006_almoxarifado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Recebimentos de Material ────────────────────────────────────────────────
    op.create_table(
        "recebimentos_material",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("processo_id", sa.Integer(), sa.ForeignKey("procurement_processes.id"), nullable=False),
        sa.Column("contrato_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id"), nullable=True),
        sa.Column("commitment_id", sa.Integer(), sa.ForeignKey("commitments.id"), nullable=True),
        sa.Column("nota_fiscal", sa.String(60), nullable=False, server_default=""),
        sa.Column("data_recebimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recebimentos_material_processo_id", "recebimentos_material", ["processo_id"])

    # ── Itens de Recebimento ────────────────────────────────────────────────────
    op.create_table(
        "itens_recebimento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recebimento_id", sa.Integer(), sa.ForeignKey("recebimentos_material.id"), nullable=False),
        sa.Column("item_almoxarifado_id", sa.Integer(), sa.ForeignKey("itens_almoxarifado.id"), nullable=False),
        sa.Column("quantidade_recebida", sa.Float(), nullable=False),
        sa.Column("valor_unitario", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("movimentacao_id", sa.Integer(), sa.ForeignKey("movimentacoes_estoque.id"), nullable=True),
    )
    op.create_index("ix_itens_recebimento_recebimento_id", "itens_recebimento", ["recebimento_id"])

    # ── Adicionar colunas de rastreabilidade em movimentacoes_estoque ──────────
    op.add_column("movimentacoes_estoque",
        sa.Column("processo_id", sa.Integer(), sa.ForeignKey("procurement_processes.id"), nullable=True))
    op.add_column("movimentacoes_estoque",
        sa.Column("contrato_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=True))
    op.add_column("movimentacoes_estoque",
        sa.Column("recebimento_id", sa.Integer(), sa.ForeignKey("recebimentos_material.id"), nullable=True))
    op.create_index("ix_movimentacoes_estoque_processo_id", "movimentacoes_estoque", ["processo_id"])
    op.create_index("ix_movimentacoes_estoque_contrato_id", "movimentacoes_estoque", ["contrato_id"])


def downgrade() -> None:
    op.drop_index("ix_movimentacoes_estoque_processo_id", "movimentacoes_estoque")
    op.drop_index("ix_movimentacoes_estoque_contrato_id", "movimentacoes_estoque")
    op.drop_column("movimentacoes_estoque", "recebimento_id")
    op.drop_column("movimentacoes_estoque", "contrato_id")
    op.drop_column("movimentacoes_estoque", "processo_id")
    op.drop_table("itens_recebimento")
    op.drop_table("recebimentos_material")
