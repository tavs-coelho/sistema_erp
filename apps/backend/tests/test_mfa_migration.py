"""Smoke-test the incremental MFA migration against a pre-MFA SQLite schema.

This is not a substitute for upgrading a real PostgreSQL deployment.
"""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_mfa_migration_upgrade_and_downgrade(monkeypatch):
    filename = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0019_user_mfa_sessions.py"
    spec = importlib.util.spec_from_file_location("migration_mfa_0019", filename)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "0006_multi_tenancy"

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        # The previous revision has a users table with an id and no session_version.
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        context = MigrationContext.configure(conn)
        monkeypatch.setattr(migration, "op", Operations(context))
        migration.upgrade()
        insp = inspect(conn)
        assert "session_version" in {c["name"] for c in insp.get_columns("users")}
        assert "user_mfa" in insp.get_table_names()
        assert "mfa_recovery_codes" in insp.get_table_names()
        assert "challenge_hash" in {c["name"] for c in insp.get_columns("user_mfa")}
        migration.downgrade()
        insp = inspect(conn)
        assert "session_version" not in {c["name"] for c in insp.get_columns("users")}
        assert "user_mfa" not in insp.get_table_names()
        assert "mfa_recovery_codes" not in insp.get_table_names()
    engine.dispose()
