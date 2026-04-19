"""Módulo Frota — Veículos, Abastecimentos e Manutenções

Revision ID: 0009_frota
Revises: 0008_alerta_estoque_requisicao
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_frota"
down_revision = "0008_alerta_estoque_requisicao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Veículos ───────────────────────────────────────────────────────────────
    op.create_table(
        "veiculos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("placa", sa.String(10), nullable=False, unique=True),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False, server_default="leve"),
        sa.Column("marca", sa.String(60), nullable=False, server_default=""),
        sa.Column("modelo", sa.String(80), nullable=False, server_default=""),
        sa.Column("ano_fabricacao", sa.Integer(), nullable=True),
        sa.Column("combustivel", sa.String(20), nullable=False, server_default="flex"),
        sa.Column("odometro_atual", sa.Float(), nullable=False, server_default="0"),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_veiculos_placa", "veiculos", ["placa"], unique=True)
    op.create_index("ix_veiculos_status", "veiculos", ["status"])

    # ── Abastecimentos ─────────────────────────────────────────────────────────
    op.create_table(
        "abastecimentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("veiculo_id", sa.Integer(), sa.ForeignKey("veiculos.id"), nullable=False),
        sa.Column("data_abastecimento", sa.Date(), nullable=False),
        sa.Column("combustivel", sa.String(20), nullable=False),
        sa.Column("litros", sa.Float(), nullable=False),
        sa.Column("valor_litro", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("odometro", sa.Float(), nullable=False, server_default="0"),
        sa.Column("posto", sa.String(120), nullable=False, server_default=""),
        sa.Column("nota_fiscal", sa.String(60), nullable=False, server_default=""),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("motorista_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("movimentacao_id", sa.Integer(), sa.ForeignKey("movimentacoes_estoque.id"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_abastecimentos_veiculo_id", "abastecimentos", ["veiculo_id"])
    op.create_index("ix_abastecimentos_data", "abastecimentos", ["data_abastecimento"])

    # ── Manutenções ────────────────────────────────────────────────────────────
    op.create_table(
        "manutencoes_veiculo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("veiculo_id", sa.Integer(), sa.ForeignKey("veiculos.id"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False, server_default="preventiva"),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("data_abertura", sa.Date(), nullable=False),
        sa.Column("data_conclusao", sa.Date(), nullable=True),
        sa.Column("odometro", sa.Float(), nullable=False, server_default="0"),
        sa.Column("oficina", sa.String(120), nullable=False, server_default=""),
        sa.Column("valor_servico", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_manutencoes_veiculo_id", "manutencoes_veiculo", ["veiculo_id"])
    op.create_index("ix_manutencoes_status", "manutencoes_veiculo", ["status"])

    # ── Itens de Manutenção ────────────────────────────────────────────────────
    op.create_table(
        "itens_manutencao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manutencao_id", sa.Integer(), sa.ForeignKey("manutencoes_veiculo.id"), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("quantidade", sa.Float(), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("item_almoxarifado_id", sa.Integer(), sa.ForeignKey("itens_almoxarifado.id"), nullable=True),
        sa.Column("movimentacao_id", sa.Integer(), sa.ForeignKey("movimentacoes_estoque.id"), nullable=True),
    )
    op.create_index("ix_itens_manutencao_manutencao_id", "itens_manutencao", ["manutencao_id"])


def downgrade() -> None:
    op.drop_table("itens_manutencao")
    op.drop_table("manutencoes_veiculo")
    op.drop_table("abastecimentos")
    op.drop_table("veiculos")
