"""Validate a fresh PostgreSQL installation using every recorded Alembic revision.

Run AFTER `alembic upgrade head` against an isolated, disposable database.
Never run a bootstrap smoke test against a production database.
"""
from sqlalchemy import inspect, text
from app.db import Base, engine
from app import models  # noqa: F401


def main() -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This validation requires PostgreSQL")
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables)
    missing_tables = sorted(expected_tables - actual_tables)
    missing_columns: dict[str, list[str]] = {}
    for name in sorted(expected_tables & actual_tables):
        expected = set(Base.metadata.tables[name].columns.keys())
        actual = {column["name"] for column in inspector.get_columns(name)}
        if expected - actual:
            missing_columns[name] = sorted(expected - actual)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    if version != "0021_tenant_core":
        raise AssertionError(f"Unexpected schema version: {version}")
    if missing_tables or missing_columns:
        raise AssertionError(
            f"ORM mismatch after migrations. Missing tables: {missing_tables}; "
            f"missing columns: {missing_columns}"
        )
    print(f"Fresh PostgreSQL installation: PASS ({len(expected_tables)} tables, revision {version})")


if __name__ == "__main__":
    main()
