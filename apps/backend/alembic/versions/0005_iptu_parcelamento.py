"""Alíquotas IPTU, parcelamento de dívida ativa

Revision ID: 0005_iptu_parcelamento
Revises: 0004_tributario
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_iptu_parcelamento"
down_revision = "0004_tributario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Alíquotas IPTU ────────────────────────────────────────────────────────
    op.create_table(
        "aliquotas_iptu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exercicio", sa.Integer(), nullable=False, index=True),
        sa.Column("uso", sa.String(30), nullable=False),
        sa.Column("aliquota", sa.Float(), nullable=False),
        sa.Column("descricao", sa.String(120), nullable=False, server_default=""),
    )

    # ── Parcelamentos de dívida ativa ─────────────────────────────────────────
    op.create_table(
        "parcelamentos_divida",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("divida_id", sa.Integer(), sa.ForeignKey("divida_ativa.id"), nullable=False),
        sa.Column("numero_parcelas", sa.Integer(), nullable=False),
        sa.Column("valor_total", sa.Float(), nullable=False),
        sa.Column("data_acordo", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── Parcelas de dívida ───────────────────────────────────────────────────
    op.create_table(
        "parcelas_divida",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parcelamento_id", sa.Integer(), sa.ForeignKey("parcelamentos_divida.id"), nullable=False),
        sa.Column("divida_id", sa.Integer(), sa.ForeignKey("divida_ativa.id"), nullable=False),
        sa.Column("numero_parcela", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("parcelas_divida")
    op.drop_table("parcelamentos_divida")
    op.drop_table("aliquotas_iptu")
