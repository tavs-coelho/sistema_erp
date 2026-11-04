"""Entity boundaries for departments, administrative protocols and uploads.

Revision ID: 0021_tenant_core
Revises: 0020_device_sessions
Existing legacy records are explicitly assigned to tenant 1 only. This does
NOT imply other business tables are tenant-safe.
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_tenant_core"
down_revision = "0020_device_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("departments", "protocolos", "attachments"):
        op.add_column(
            table, sa.Column("tenant_id", sa.Integer(),
                             sa.ForeignKey("tenant_branding.id"),
                             nullable=False, server_default="1"),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # The legacy global name uniqueness prevents different municipalities from
    # having a department called "Administração". Enforce per-entity uniqueness.
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("departments_name_key", "departments", type_="unique")
    else:
        with op.batch_alter_table("departments") as batch:
            batch.drop_constraint("departments_name_key", type_="unique")
    op.create_unique_constraint(
        "uq_departments_tenant_name", "departments", ["tenant_id", "name"]
    )


def downgrade() -> None:
    # A downgrade to globally unique departments can fail once different
    # entities register the same name. Never downgrade without data review.
    op.drop_constraint("uq_departments_tenant_name", "departments", type_="unique")
    op.create_unique_constraint("departments_name_key", "departments", ["name"])
    for table in ("attachments", "protocolos", "departments"):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
