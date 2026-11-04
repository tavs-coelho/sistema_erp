"""Testes de regressão da política fail-closed, independentes de banco real."""
import pytest
from fastapi import HTTPException
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.finance_tenant import TenantIsolationError, require_owned, require_tenant_id, tenant_query


class Base(DeclarativeBase):
    pass


class Entry(Base):
    __tablename__ = "finance_test_entries"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=False)


class LegacyEntry(Base):
    __tablename__ = "finance_test_legacy"
    id = Column(Integer, primary_key=True)


@pytest.mark.parametrize("value", [None, 0, -1, True, "1"])
def test_invalid_tenant_rejected(value):
    with pytest.raises(HTTPException) as error:
        require_tenant_id(value)
    assert error.value.status_code == 403


def test_owned_record_indistinguishable_from_missing():
    assert require_owned(Entry(id=1, tenant_id=2), 2).id == 1
    for record in [None, Entry(id=1, tenant_id=2)]:
        with pytest.raises(HTTPException) as error:
            require_owned(record, 1)
        assert error.value.status_code == 404


def test_legacy_model_fails_closed():
    with pytest.raises(TenantIsolationError):
        require_owned(LegacyEntry(id=1), 1)


def test_scoped_query_hides_other_tenants():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Entry(tenant_id=1), Entry(tenant_id=2), Entry(tenant_id=2)])
        db.commit()
        assert tenant_query(db.query(Entry), Entry, 1).count() == 1
        assert tenant_query(db.query(Entry), Entry, 2).count() == 2
        with pytest.raises(TenantIsolationError):
            tenant_query(db.query(LegacyEntry), LegacyEntry, 1)
