"""Validate migration 0020 and refresh locking with a real PostgreSQL server.

Intentionally bootstraps a synthetic schema matching the preceding ORM model
except for user_sessions, then stamps revision 0019. This does NOT verify the
historical 0001..0019 migration chain.
"""
import sys

from fastapi import Request
from jose import jwt
from sqlalchemy import inspect

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import RoleEnum, TenantBranding, User, UserSession
from app.security import hash_password
from app.session_service import create_device_session, rotate_refresh_token, valid_session


def bootstrap() -> None:
    assert engine.dialect.name == "postgresql", "This check must run on PostgreSQL"
    tables = [table for table in Base.metadata.sorted_tables if table.name != "user_sessions"]
    Base.metadata.create_all(bind=engine, tables=tables)
    assert "user_sessions" not in inspect(engine).get_table_names()


def verify() -> None:
    assert engine.dialect.name == "postgresql"
    assert "user_sessions" in inspect(engine).get_table_names()
    with SessionLocal() as db:
        db.add(TenantBranding(id=1, org_name="CI Test Entity", subdomain="ci-test"))
        db.add(User(
            id=921, username="ci-session", full_name="CI Session",
            email="ci-session@example.org", role=RoleEnum.admin,
            hashed_password=hash_password("ci-password-is-not-production"),
            tenant_id=1, active=True, session_version=0,
        ))
        db.commit()
        user = db.get(User, 921)
        req = Request({"type": "http", "headers": [(b"user-agent", b"CI PostgreSQL")]})
        tokens = create_device_session(db, user, 1, req)
        sid = jwt.decode(tokens.access_token, settings.secret_key, algorithms=[settings.algorithm])["sid"]
        assert valid_session(db.get(UserSession, sid), user, 1)
        rotated = rotate_refresh_token(db, user, 1, sid, tokens.refresh_token)
        assert rotated and rotated.refresh_token != tokens.refresh_token
        assert rotate_refresh_token(db, user, 1, sid, tokens.refresh_token) is None
        db.expire_all()
        assert not valid_session(db.get(UserSession, sid), user, 1)
    print("PostgreSQL migration + refresh rotation/replay: PASSED")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("bootstrap", "verify"):
        raise SystemExit("usage: verify_postgres_device_session.py bootstrap|verify")
    {"bootstrap": bootstrap, "verify": verify}[sys.argv[1]]()
