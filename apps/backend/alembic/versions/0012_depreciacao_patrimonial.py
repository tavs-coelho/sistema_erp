"""Depreciação Patrimonial (NBCASP/IPSAS 17)

Revision ID: 0012_depreciacao_patrimonial
Revises: 0011_ponto_frequencia
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_depreciacao_patrimonial"
down_revision = "0011_ponto_frequencia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Configurações de depreciação por bem ──────────────────────────────────
    op.create_table(
        "configuracoes_depreciacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False, unique=True),
        sa.Column("data_aquisicao", sa.Date(), nullable=False),
        sa.Column("valor_aquisicao", sa.Float(), nullable=False),
        sa.Column("vida_util_meses", sa.Integer(), nullable=False),
        sa.Column("valor_residual", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metodo", sa.String(30), nullable=False, server_default="linear"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.create_index("ix_configuracoes_depreciacao_asset_id", "configuracoes_depreciacao", ["asset_id"])

    # ── Lançamentos mensais de depreciação ────────────────────────────────────
    op.create_table(
        "lancamentos_depreciacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("valor_depreciado", sa.Float(), nullable=False),
        sa.Column("depreciacao_acumulada", sa.Float(), nullable=False),
        sa.Column("valor_contabil_liquido", sa.Float(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lancamentos_depreciacao_asset_id", "lancamentos_depreciacao", ["asset_id"])
    op.create_index("ix_lancamentos_depreciacao_periodo", "lancamentos_depreciacao", ["periodo"])


def downgrade() -> None:
    op.drop_table("lancamentos_depreciacao")
    op.drop_table("configuracoes_depreciacao")
