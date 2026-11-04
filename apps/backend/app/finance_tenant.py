"""Primitivas de isolamento de entidades para fluxos financeiros.

Uso obrigatório após migração das tabelas financeiras para tenant_id.
Não aplica fallback de tenant 1: erro de configuração é bloqueante.
"""
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Query

T = TypeVar("T")


class TenantIsolationError(RuntimeError):
    """O modelo consultado ainda não tem isolamento multi-entidade."""


def require_tenant_id(tenant_id: int | None) -> int:
    if not isinstance(tenant_id, int) or isinstance(tenant_id, bool) or tenant_id < 1:
        raise HTTPException(status_code=403, detail="Entidade não identificada")
    return tenant_id


def tenant_query(query: Query, model: type[T], tenant_id: int | None) -> Query:
    """Restringe a consulta ANTES de filtros, paginação e agregações."""
    tid = require_tenant_id(tenant_id)
    if not hasattr(model, "tenant_id"):
        raise TenantIsolationError(f"{model.__name__} sem coluna tenant_id")
    return query.filter(model.tenant_id == tid)


def require_owned(record: T | None, tenant_id: int | None) -> T:
    """Resposta indistinguível para registro ausente e de outra entidade."""
    tid = require_tenant_id(tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    if not hasattr(record, "tenant_id"):
        raise TenantIsolationError(f"{type(record).__name__} sem coluna tenant_id")
    if record.tenant_id != tid:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return record
