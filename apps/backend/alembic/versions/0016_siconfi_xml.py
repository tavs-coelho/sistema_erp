"""Onda 19 — SICONFI Fase 1: tabelas para log de validação XML e envio real (stub)

Revision ID: 0016_siconfi_xml
Revises: 0015_siconfi_siop
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_siconfi_xml"
down_revision = "0015_siconfi_siop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validacoes_xml_siconfi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(20), nullable=True),
        sa.Column("valido", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("erros_xsd", sa.JSON(), nullable=True),
        sa.Column("avisos", sa.JSON(), nullable=True),
        sa.Column("xml_gerado", sa.Text(), nullable=True),
        sa.Column("xsd_fonte", sa.String(80), nullable=False, server_default="inline"),
        sa.Column("gerado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_validacoes_xml_tipo", "validacoes_xml_siconfi", ["tipo"])
    op.create_index("ix_validacoes_xml_exercicio", "validacoes_xml_siconfi", ["exercicio"])

    op.create_table(
        "envios_siconfi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("validacao_xml_id", sa.Integer(), sa.ForeignKey("validacoes_xml_siconfi.id"), nullable=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("protocolo", sa.String(100), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("resposta_raw", sa.Text(), nullable=True),
        sa.Column("erro_detalhe", sa.Text(), nullable=True),
        sa.Column("certificado_serial", sa.String(80), nullable=True),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enviado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_envios_siconfi_tipo", "envios_siconfi", ["tipo"])
    op.create_index("ix_envios_siconfi_exercicio", "envios_siconfi", ["exercicio"])


def downgrade() -> None:
    op.drop_table("envios_siconfi")
    op.drop_table("validacoes_xml_siconfi")
