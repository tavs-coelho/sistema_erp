"""Camada preparatória SICONFI / SIOP

Revision ID: 0015_siconfi_siop
Revises: 0014_recalculo_payslip
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_siconfi_siop"
down_revision = "0014_recalculo_payslip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracoes_entidade",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome_entidade", sa.String(200), nullable=False),
        sa.Column("cnpj", sa.String(18), nullable=False),
        sa.Column("codigo_ibge", sa.String(7), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("esfera", sa.String(20), nullable=False, server_default="Municipal"),
        sa.Column("poder", sa.String(20), nullable=False, server_default="Executivo"),
        sa.Column("tipo_entidade", sa.String(40), nullable=False, server_default="Prefeitura Municipal"),
        sa.Column("responsavel_nome", sa.String(120), nullable=False, server_default=""),
        sa.Column("responsavel_cargo", sa.String(80), nullable=False, server_default=""),
        sa.Column("responsavel_cpf", sa.String(14), nullable=False, server_default=""),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "exportacoes_siconfi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("inconsistencias", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("gerado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exportacoes_siconfi_tipo", "exportacoes_siconfi", ["tipo"])
    op.create_index("ix_exportacoes_siconfi_exercicio", "exportacoes_siconfi", ["exercicio"])


def downgrade() -> None:
    op.drop_table("exportacoes_siconfi")
    op.drop_table("configuracoes_entidade")
