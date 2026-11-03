"""Regression tests for the historically bounded Alembic initial revision."""
import importlib.util
from pathlib import Path


def _historical_baseline():
    location = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial.py"
    spec = importlib.util.spec_from_file_location("initial_0001", location)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_baseline_excludes_all_later_migration_tables():
    revision = _historical_baseline()
    metadata = revision._initial_metadata()
    names = set(metadata.tables)
    assert {"users", "employees", "audit_logs", "attachments", "commitments"} <= names
    assert "tenant_branding" not in names
    assert "user_mfa" not in names
    assert "user_sessions" not in names
    assert "ppas" not in names
    assert "protocolos" not in names
    assert "contribuintes" not in names
    assert "veiculos" not in names


def test_initial_users_exclude_columns_added_by_later_migrations():
    tables = _historical_baseline()._initial_metadata().tables
    assert "active" not in tables["users"].c
    assert "tenant_id" not in tables["users"].c
    assert "session_version" not in tables["users"].c
    assert "active" not in tables["departments"].c
    assert "loa_item_id" not in tables["commitments"].c
