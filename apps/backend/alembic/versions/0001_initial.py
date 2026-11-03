"""Initial schema as it existed before the additive Alembic revisions.

Revision ID: 0001_initial
Revises:

Historical warning:
  The original migration called Base.metadata.create_all() using the *current*
  model. On a new database it also created tables/columns that later migrations
  attempted to add again. This explicit baseline creates only the original
  core tables and omits columns introduced in later migrations.

  Preserve this set and keep it covered by the fresh-PostgreSQL CI job.
"""

from alembic import op
from sqlalchemy import Column, MetaData, Table

from app.db import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# Frozen column list for the pre-0002 core schema. Future ORM additions are
# NEVER inserted into revision 0001 implicitly: add a new revision instead.
# Column SQL types are copied from the ORM; type changes still require review.
_INITIAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "municipalities": ("id", "name"),
    "departments": ("id", "name"),
    "fiscal_years": ("id", "year", "active"),
    "employees": ("id", "name", "cpf", "job_title", "employment_type", "base_salary", "department_id"),
    "users": ("id", "username", "full_name", "email", "hashed_password", "role", "must_change_password", "employee_id"),
    "vendors": ("id", "name", "document"),
    "budget_allocations": ("id", "code", "description", "amount", "fiscal_year_id"),
    "funding_sources": ("id", "code", "name"),
    "commitments": ("id", "number", "description", "amount", "status", "fiscal_year_id", "department_id", "vendor_id"),
    "liquidations": ("id", "commitment_id", "amount", "created_at"),
    "payments": ("id", "commitment_id", "amount", "payment_date"),
    "revenue_entries": ("id", "description", "amount", "entry_date"),
    "procurement_processes": ("id", "number", "object_description", "status"),
    "contracts": ("id", "number", "process_id", "vendor_id", "start_date", "end_date", "amount", "status"),
    "contract_addenda": ("id", "contract_id", "description", "amount_delta"),
    "assets": ("id", "tag", "description", "classification", "location", "department_id", "responsible_employee_id", "value", "status"),
    "asset_movements": ("id", "asset_id", "from_department_id", "to_department_id", "movement_type", "moved_at"),
    "payroll_events": ("id", "employee_id", "month", "kind", "description", "value"),
    "payslips": ("id", "employee_id", "month", "gross_amount", "deductions", "net_amount"),
    "attachments": ("id", "entity_type", "entity_id", "file_name", "path"),
    "audit_logs": ("id", "user_id", "action", "entity", "entity_id", "before_data", "after_data", "created_at"),
    "password_reset_tokens": ("id", "user_id", "token", "expires_at"),
    "contas_bancarias": ("id", "banco", "agencia", "numero_conta", "descricao", "tipo", "ativa", "saldo_inicial", "data_saldo_inicial", "created_at"),
    "lancamentos_bancarios": ("id", "conta_id", "data_lancamento", "tipo", "valor", "descricao", "documento_ref", "status", "payment_id", "revenue_entry_id", "divergencia_obs", "conciliado_em", "conciliado_por_id", "created_at"),
}


def _initial_metadata() -> MetaData:
    metadata = MetaData()
    for name, column_names in _INITIAL_COLUMNS.items():
        source = Base.metadata.tables[name]
        columns: list[Column] = [source.c[column_name].copy() for column_name in column_names]
        Table(name, metadata, *columns)
    return metadata

def upgrade() -> None:
    bind = op.get_bind()
    # Alembic creates version_num VARCHAR(32) by default, but historical
    # revision identifiers exceed 32 characters (e.g. 0007_integracao_*).
    # Expand only on PostgreSQL before recording those revisions.
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")
    _initial_metadata().create_all(bind=bind, checkfirst=False)


def downgrade() -> None:
    _initial_metadata().drop_all(bind=op.get_bind(), checkfirst=False)
