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

# Legacy core tables, all others are created by revisions 0002..0020.
# There are deliberately NO branding, MFA or other later module tables here.
_BASELINE_TABLES = (
    "municipalities",
    "departments",
    "fiscal_years",
    "employees",
    "users",
    "vendors",
    "budget_allocations",
    "funding_sources",
    "commitments",
    "liquidations",
    "payments",
    "revenue_entries",
    "procurement_processes",
    "contracts",
    "contract_addenda",
    "assets",
    "asset_movements",
    "payroll_events",
    "payslips",
    "attachments",
    "audit_logs",
    "password_reset_tokens",
    "contas_bancarias",
    "lancamentos_bancarios",
)

# Columns are introduced by these later revisions and must be absent here.
_ADDED_LATER = {
    "departments": {"active"},              # 0002
    "users": {"active", "tenant_id", "session_version"},  # 0002, multi-tenancy, MFA
    "commitments": {"loa_item_id"},           # 0017
}


def _initial_metadata() -> MetaData:
    metadata = MetaData()
    for name in _BASELINE_TABLES:
        source = Base.metadata.tables[name]
        excluded = _ADDED_LATER.get(name, set())
        # Column.copy keeps historical FK, unique/index and default metadata
        # while avoiding later ORM relationships and duplicate tables.
        columns: list[Column] = [
            column.copy() for column in source.columns if column.name not in excluded
        ]
        Table(name, metadata, *columns)
    return metadata


def upgrade() -> None:
    _initial_metadata().create_all(bind=op.get_bind(), checkfirst=False)


def downgrade() -> None:
    _initial_metadata().drop_all(bind=op.get_bind(), checkfirst=False)
