"""Smoke test for migration 0020, isolated from legacy bootstrap migrations."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_device_session_migration_up_down(monkeypatch):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic" / "versions" / "0020_device_sessions.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0020_sessions", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "0019_user_mfa_sessions"
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE tenant_branding (id INTEGER PRIMARY KEY)"))
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(conn)),
        )
        migration.upgrade()
        inspector = inspect(conn)
        assert "user_sessions" in inspector.get_table_names()
        columns = {column["name"] for column in inspector.get_columns("user_sessions")}
        assert {
            "id", "user_id", "tenant_id", "session_version",
            "refresh_token_hash", "created_at", "last_used_at", "expires_at",
            "revoked_at", "user_agent",
        } <= columns
        migration.downgrade()
        assert "user_sessions" not in inspect(conn).get_table_names()
    engine.dispose()
