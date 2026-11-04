"""Document management and immutable versions.

Revision ID: 0025_municipal_documents
Revises: 0024_municipal_assignments
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_municipal_documents"
down_revision = "0024_municipal_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipal_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("classification", sa.String(16), nullable=False, server_default="interno"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ativo"),
        sa.Column("protocol_id", sa.Integer(), sa.ForeignKey("protocolos.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_municipal_documents_code"),
        sa.CheckConstraint("classification IN ('publico','interno','restrito')", name="ck_municipal_documents_class"),
        sa.CheckConstraint("status IN ('ativo','arquivado')", name="ck_municipal_documents_status"),
    )
    op.create_index("ix_municipal_documents_tenant_id", "municipal_documents", ["tenant_id"])
    op.create_table(
        "municipal_document_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("municipal_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenant_branding.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_name", sa.String(180), nullable=False),
        sa.Column("storage_key", sa.String(320), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "version", name="uq_municipal_document_version"),
    )
    op.create_index("ix_municipal_document_versions_document_id", "municipal_document_versions", ["document_id"])
    op.create_index("ix_municipal_document_versions_tenant_id", "municipal_document_versions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_municipal_document_versions_tenant_id", table_name="municipal_document_versions")
    op.drop_index("ix_municipal_document_versions_document_id", table_name="municipal_document_versions")
    op.drop_table("municipal_document_versions")
    op.drop_index("ix_municipal_documents_tenant_id", table_name="municipal_documents")
    op.drop_table("municipal_documents")
