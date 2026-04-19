"""NFS-e e ITBI — Notas Fiscais de Serviços e ITBI

Revision ID: 0010_nfse_itbi
Revises: 0009_frota
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_nfse_itbi"
down_revision = "0009_frota"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Notas Fiscais de Serviços (NFS-e) ────────────────────────────────────
    op.create_table(
        "notas_fiscais_servico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.String(20), nullable=False, unique=True),
        sa.Column("prestador_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=False),
        sa.Column("tomador_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=True),
        sa.Column("descricao_servico", sa.Text(), nullable=False, server_default=""),
        sa.Column("codigo_servico", sa.String(20), nullable=False, server_default=""),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("valor_servico", sa.Float(), nullable=False),
        sa.Column("valor_deducoes", sa.Float(), nullable=False, server_default="0"),
        sa.Column("aliquota_iss", sa.Float(), nullable=False),
        sa.Column("valor_iss", sa.Float(), nullable=False),
        sa.Column("retencao_fonte", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="emitida"),
        sa.Column("nota_substituta_id", sa.Integer(), sa.ForeignKey("notas_fiscais_servico.id"), nullable=True),
        sa.Column("lancamento_id", sa.Integer(), sa.ForeignKey("lancamentos_tributarios.id"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notas_fiscais_servico_numero", "notas_fiscais_servico", ["numero"])
    op.create_index("ix_notas_fiscais_servico_prestador_id", "notas_fiscais_servico", ["prestador_id"])
    op.create_index("ix_notas_fiscais_servico_data_emissao", "notas_fiscais_servico", ["data_emissao"])
    op.create_index("ix_notas_fiscais_servico_status", "notas_fiscais_servico", ["status"])

    # ── Operações ITBI ────────────────────────────────────────────────────────
    op.create_table(
        "operacoes_itbi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.String(20), nullable=False, unique=True),
        sa.Column("transmitente_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=False),
        sa.Column("adquirente_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=False),
        sa.Column("imovel_id", sa.Integer(), sa.ForeignKey("imoveis_cadastrais.id"), nullable=False),
        sa.Column("natureza_operacao", sa.String(40), nullable=False, server_default="compra_venda"),
        sa.Column("data_operacao", sa.Date(), nullable=False),
        sa.Column("valor_declarado", sa.Float(), nullable=False),
        sa.Column("valor_venal_referencia", sa.Float(), nullable=False, server_default="0"),
        sa.Column("base_calculo", sa.Float(), nullable=False),
        sa.Column("aliquota_itbi", sa.Float(), nullable=False),
        sa.Column("valor_devido", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberto"),
        sa.Column("lancamento_id", sa.Integer(), sa.ForeignKey("lancamentos_tributarios.id"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operacoes_itbi_numero", "operacoes_itbi", ["numero"])
    op.create_index("ix_operacoes_itbi_transmitente_id", "operacoes_itbi", ["transmitente_id"])
    op.create_index("ix_operacoes_itbi_adquirente_id", "operacoes_itbi", ["adquirente_id"])
    op.create_index("ix_operacoes_itbi_imovel_id", "operacoes_itbi", ["imovel_id"])
    op.create_index("ix_operacoes_itbi_data_operacao", "operacoes_itbi", ["data_operacao"])
    op.create_index("ix_operacoes_itbi_status", "operacoes_itbi", ["status"])


def downgrade() -> None:
    op.drop_table("operacoes_itbi")
    op.drop_table("notas_fiscais_servico")
