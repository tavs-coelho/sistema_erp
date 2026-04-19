"""Tributário: contribuintes, imóveis, lançamentos, guias, dívida ativa

Revision ID: 0004_tributario
Revises: 0003_protocolo_convenios
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_tributario"
down_revision = "0003_protocolo_convenios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Contribuintes ─────────────────────────────────────────────────────────
    op.create_table(
        "contribuintes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cpf_cnpj", sa.String(18), nullable=False, unique=True),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("tipo", sa.String(2), nullable=False, server_default="PF"),
        sa.Column("email", sa.String(160), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("logradouro", sa.String(200), nullable=False, server_default=""),
        sa.Column("numero", sa.String(10), nullable=False, server_default=""),
        sa.Column("complemento", sa.String(80), nullable=False, server_default=""),
        sa.Column("bairro", sa.String(80), nullable=False, server_default=""),
        sa.Column("municipio", sa.String(80), nullable=False, server_default=""),
        sa.Column("uf", sa.String(2), nullable=False, server_default=""),
        sa.Column("cep", sa.String(9), nullable=False, server_default=""),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_contribuintes_cpf_cnpj", "contribuintes", ["cpf_cnpj"], unique=True)

    # ── Cadastro Imobiliário ───────────────────────────────────────────────────
    op.create_table(
        "imoveis_cadastrais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inscricao", sa.String(30), nullable=False, unique=True),
        sa.Column("contribuinte_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=False),
        sa.Column("logradouro", sa.String(200), nullable=False),
        sa.Column("numero", sa.String(10), nullable=False, server_default=""),
        sa.Column("complemento", sa.String(80), nullable=False, server_default=""),
        sa.Column("bairro", sa.String(80), nullable=False, server_default=""),
        sa.Column("area_terreno", sa.Float(), nullable=False, server_default="0"),
        sa.Column("area_construida", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_venal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uso", sa.String(30), nullable=False, server_default="residencial"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.create_index("ix_imoveis_cadastrais_inscricao", "imoveis_cadastrais", ["inscricao"], unique=True)

    # ── Lançamentos Tributários ────────────────────────────────────────────────
    op.create_table(
        "lancamentos_tributarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contribuinte_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=False),
        sa.Column("imovel_id", sa.Integer(), sa.ForeignKey("imoveis_cadastrais.id"), nullable=True),
        sa.Column("tributo", sa.String(20), nullable=False),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("valor_principal", sa.Float(), nullable=False),
        sa.Column("valor_juros", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_multa", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_desconto", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_total", sa.Float(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberto"),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── Guias de Arrecadação ───────────────────────────────────────────────────
    op.create_table(
        "guias_pagamento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lancamento_id", sa.Integer(), sa.ForeignKey("lancamentos_tributarios.id"), nullable=False),
        sa.Column("codigo_barras", sa.String(80), nullable=False, unique=True),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="emitida"),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("banco", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_guias_pagamento_codigo_barras", "guias_pagamento", ["codigo_barras"], unique=True)

    # ── Dívida Ativa ───────────────────────────────────────────────────────────
    op.create_table(
        "divida_ativa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lancamento_id", sa.Integer(), sa.ForeignKey("lancamentos_tributarios.id"), nullable=False, unique=True),
        sa.Column("contribuinte_id", sa.Integer(), sa.ForeignKey("contribuintes.id"), nullable=False),
        sa.Column("numero_inscricao", sa.String(30), nullable=False, unique=True),
        sa.Column("tributo", sa.String(20), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("valor_original", sa.Float(), nullable=False),
        sa.Column("valor_atualizado", sa.Float(), nullable=False),
        sa.Column("data_inscricao", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativa"),
        sa.Column("data_ajuizamento", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_divida_ativa_numero_inscricao", "divida_ativa", ["numero_inscricao"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_divida_ativa_numero_inscricao", table_name="divida_ativa")
    op.drop_table("divida_ativa")
    op.drop_index("ix_guias_pagamento_codigo_barras", table_name="guias_pagamento")
    op.drop_table("guias_pagamento")
    op.drop_table("lancamentos_tributarios")
    op.drop_index("ix_imoveis_cadastrais_inscricao", table_name="imoveis_cadastrais")
    op.drop_table("imoveis_cadastrais")
    op.drop_index("ix_contribuintes_cpf_cnpj", table_name="contribuintes")
    op.drop_table("contribuintes")
