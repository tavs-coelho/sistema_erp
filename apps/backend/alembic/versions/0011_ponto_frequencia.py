"""Ponto e Frequência de Servidores

Revision ID: 0011_ponto_frequencia
Revises: 0010_nfse_itbi
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_ponto_frequencia"
down_revision = "0010_nfse_itbi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Escalas (carga horária contratual) ───────────────────────────────────
    op.create_table(
        "escalas_servidores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False, unique=True),
        sa.Column("horas_dia", sa.Float(), nullable=False, server_default="8.0"),
        sa.Column("dias_semana", sa.String(7), nullable=False, server_default="12345"),
        sa.Column("hora_entrada", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("hora_saida", sa.String(5), nullable=False, server_default="17:00"),
        sa.Column("hora_inicio_intervalo", sa.String(5), nullable=False, server_default="12:00"),
        sa.Column("hora_fim_intervalo", sa.String(5), nullable=False, server_default="13:00"),
    )
    op.create_index("ix_escalas_servidores_employee_id", "escalas_servidores", ["employee_id"])

    # ── Registros de Ponto ───────────────────────────────────────────────────
    op.create_table(
        "registros_ponto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tipo_registro", sa.String(20), nullable=False),
        sa.Column("hora_registro", sa.String(5), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("observacoes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_registros_ponto_employee_id", "registros_ponto", ["employee_id"])
    op.create_index("ix_registros_ponto_data", "registros_ponto", ["data"])

    # ── Abonos de Falta ──────────────────────────────────────────────────────
    op.create_table(
        "abonos_falta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="falta"),
        sa.Column("motivo", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("aprovado_por_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_abonos_falta_employee_id", "abonos_falta", ["employee_id"])
    op.create_index("ix_abonos_falta_data", "abonos_falta", ["data"])
    op.create_index("ix_abonos_falta_status", "abonos_falta", ["status"])


def downgrade() -> None:
    op.drop_table("abonos_falta")
    op.drop_table("registros_ponto")
    op.drop_table("escalas_servidores")
