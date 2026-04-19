"""Almoxarifado: itens, movimentações de estoque

Revision ID: 0006_almoxarifado
Revises: 0005_iptu_parcelamento
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_almoxarifado"
down_revision = "0005_iptu_parcelamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "itens_almoxarifado",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(30), nullable=False, unique=True),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("unidade", sa.String(10), nullable=False),
        sa.Column("categoria", sa.String(60), nullable=False, server_default="geral"),
        sa.Column("localizacao", sa.String(80), nullable=False, server_default=""),
        sa.Column("estoque_minimo", sa.Float(), nullable=False, server_default="0"),
        sa.Column("estoque_atual", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_unitario", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_itens_almoxarifado_codigo", "itens_almoxarifado", ["codigo"])

    op.create_table(
        "movimentacoes_estoque",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("itens_almoxarifado.id"), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("quantidade", sa.Float(), nullable=False),
        sa.Column("valor_unitario", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("data_movimentacao", sa.Date(), nullable=False),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("documento_ref", sa.String(80), nullable=False, server_default=""),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("saldo_pos", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_movimentacoes_estoque_item_id", "movimentacoes_estoque", ["item_id"])


def downgrade() -> None:
    op.drop_table("movimentacoes_estoque")
    op.drop_table("itens_almoxarifado")
