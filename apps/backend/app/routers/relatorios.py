"""Router Relatórios — Custos Operacionais Consolidados.

Cobre:
  - Custo total por veículo e período (abastecimento + manutenção serviço + peças almoxarifado)
  - Custo total por departamento e período (mesma composição)
  - Exportação CSV para ambos os relatórios
  - Filtros: data_inicio, data_fim, veiculo_id, departamento_id
"""

import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import (
    Abastecimento,
    Department,
    ItemManutencao,
    ManutencaoVeiculo,
    User,
    Veiculo,
)

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ab_agg(db: Session, data_inicio, data_fim):
    """Agrega custos de abastecimento por veiculo_id."""
    q = db.query(
        Abastecimento.veiculo_id,
        func.coalesce(func.sum(Abastecimento.valor_total), 0.0).label("custo"),
        func.count(Abastecimento.id).label("n"),
        func.coalesce(func.sum(Abastecimento.litros), 0.0).label("litros"),
    )
    if data_inicio:
        q = q.filter(Abastecimento.data_abastecimento >= data_inicio)
    if data_fim:
        q = q.filter(Abastecimento.data_abastecimento <= data_fim)
    return {r.veiculo_id: r for r in q.group_by(Abastecimento.veiculo_id).all()}


def _man_agg(db: Session, data_inicio, data_fim):
    """Agrega custos de serviço de manutenção por veiculo_id."""
    q = db.query(
        ManutencaoVeiculo.veiculo_id,
        func.coalesce(func.sum(ManutencaoVeiculo.valor_servico), 0.0).label("custo"),
        func.count(ManutencaoVeiculo.id).label("n"),
    )
    if data_inicio:
        q = q.filter(ManutencaoVeiculo.data_abertura >= data_inicio)
    if data_fim:
        q = q.filter(ManutencaoVeiculo.data_abertura <= data_fim)
    return {r.veiculo_id: r for r in q.group_by(ManutencaoVeiculo.veiculo_id).all()}


def _pecas_agg(db: Session, data_inicio, data_fim):
    """Agrega custo de peças/insumos do almoxarifado consumidos em manutenções por veiculo_id."""
    q = db.query(
        ManutencaoVeiculo.veiculo_id,
        func.coalesce(func.sum(ItemManutencao.valor_total), 0.0).label("custo"),
        func.count(ItemManutencao.id).label("n"),
    ).join(ItemManutencao, ItemManutencao.manutencao_id == ManutencaoVeiculo.id)
    if data_inicio:
        q = q.filter(ManutencaoVeiculo.data_abertura >= data_inicio)
    if data_fim:
        q = q.filter(ManutencaoVeiculo.data_abertura <= data_fim)
    return {r.veiculo_id: r for r in q.group_by(ManutencaoVeiculo.veiculo_id).all()}


def _ab_dept_agg(db: Session, data_inicio, data_fim):
    """Agrega custos de abastecimento por departamento_id."""
    q = db.query(
        Abastecimento.departamento_id,
        func.coalesce(func.sum(Abastecimento.valor_total), 0.0).label("custo"),
        func.count(Abastecimento.id).label("n"),
        func.coalesce(func.sum(Abastecimento.litros), 0.0).label("litros"),
    )
    if data_inicio:
        q = q.filter(Abastecimento.data_abastecimento >= data_inicio)
    if data_fim:
        q = q.filter(Abastecimento.data_abastecimento <= data_fim)
    return {r.departamento_id: r for r in q.group_by(Abastecimento.departamento_id).all()}


def _man_dept_agg(db: Session, data_inicio, data_fim):
    """Agrega custo de serviço de manutenção por departamento_id."""
    q = db.query(
        ManutencaoVeiculo.departamento_id,
        func.coalesce(func.sum(ManutencaoVeiculo.valor_servico), 0.0).label("custo"),
        func.count(ManutencaoVeiculo.id).label("n"),
    )
    if data_inicio:
        q = q.filter(ManutencaoVeiculo.data_abertura >= data_inicio)
    if data_fim:
        q = q.filter(ManutencaoVeiculo.data_abertura <= data_fim)
    return {r.departamento_id: r for r in q.group_by(ManutencaoVeiculo.departamento_id).all()}


def _pecas_dept_agg(db: Session, data_inicio, data_fim):
    """Agrega custo de peças/insumos do almoxarifado por departamento_id da manutenção."""
    q = db.query(
        ManutencaoVeiculo.departamento_id,
        func.coalesce(func.sum(ItemManutencao.valor_total), 0.0).label("custo"),
        func.count(ItemManutencao.id).label("n"),
    ).join(ItemManutencao, ItemManutencao.manutencao_id == ManutencaoVeiculo.id)
    if data_inicio:
        q = q.filter(ManutencaoVeiculo.data_abertura >= data_inicio)
    if data_fim:
        q = q.filter(ManutencaoVeiculo.data_abertura <= data_fim)
    return {r.departamento_id: r for r in q.group_by(ManutencaoVeiculo.departamento_id).all()}


def _build_veiculo_row(v: Veiculo, ab_map, man_map, pecas_map) -> dict:
    ab = ab_map.get(v.id)
    man = man_map.get(v.id)
    pecas = pecas_map.get(v.id)
    custo_ab = round(float(ab.custo if ab else 0), 2)
    custo_man = round(float(man.custo if man else 0), 2)
    custo_pecas = round(float(pecas.custo if pecas else 0), 2)
    return {
        "veiculo_id": v.id,
        "placa": v.placa,
        "descricao": v.descricao,
        "tipo": v.tipo,
        "combustivel": v.combustivel,
        "departamento_id": v.departamento_id,
        "n_abastecimentos": int(ab.n if ab else 0),
        "total_litros": round(float(ab.litros if ab else 0), 2),
        "custo_abastecimento": custo_ab,
        "n_manutencoes": int(man.n if man else 0),
        "custo_manutencao_servico": custo_man,
        "n_pecas_almoxarifado": int(pecas.n if pecas else 0),
        "custo_pecas_almoxarifado": custo_pecas,
        "custo_total": round(custo_ab + custo_man + custo_pecas, 2),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/frota/custo-por-veiculo", response_model=None)
def custo_por_veiculo(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    veiculo_id: int | None = None,
    departamento_id: int | None = None,
    export: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório de custo operacional por veículo.

    Composição: abastecimento + serviço manutenção + peças/insumos do almoxarifado.
    Filtros: data_inicio, data_fim, veiculo_id, departamento_id.
    Parâmetro export=csv retorna arquivo CSV.
    """
    ab_map = _ab_agg(db, data_inicio, data_fim)
    man_map = _man_agg(db, data_inicio, data_fim)
    pecas_map = _pecas_agg(db, data_inicio, data_fim)

    q = db.query(Veiculo)
    if veiculo_id:
        q = q.filter(Veiculo.id == veiculo_id)
    if departamento_id:
        q = q.filter(Veiculo.departamento_id == departamento_id)
    q = q.order_by(Veiculo.placa)

    rows = [_build_veiculo_row(v, ab_map, man_map, pecas_map) for v in q.all()]

    # Totais
    totals = {
        "total_veiculos": len(rows),
        "total_abastecimento": round(sum(r["custo_abastecimento"] for r in rows), 2),
        "total_manutencao_servico": round(sum(r["custo_manutencao_servico"] for r in rows), 2),
        "total_pecas_almoxarifado": round(sum(r["custo_pecas_almoxarifado"] for r in rows), 2),
        "total_geral": round(sum(r["custo_total"] for r in rows), 2),
    }

    if export == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "veiculo_id", "placa", "descricao", "tipo", "combustivel", "departamento_id",
            "n_abastecimentos", "total_litros", "custo_abastecimento",
            "n_manutencoes", "custo_manutencao_servico",
            "n_pecas_almoxarifado", "custo_pecas_almoxarifado", "custo_total",
        ])
        for r in rows:
            writer.writerow([
                r["veiculo_id"], r["placa"], r["descricao"], r["tipo"], r["combustivel"],
                r["departamento_id"], r["n_abastecimentos"], r["total_litros"],
                r["custo_abastecimento"], r["n_manutencoes"], r["custo_manutencao_servico"],
                r["n_pecas_almoxarifado"], r["custo_pecas_almoxarifado"], r["custo_total"],
            ])
        fname = "custo_por_veiculo"
        if data_inicio:
            fname += f"_{data_inicio}"
        if data_fim:
            fname += f"_{data_fim}"
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={fname}.csv"},
        )

    return {"filtros": {"data_inicio": data_inicio, "data_fim": data_fim,
                        "veiculo_id": veiculo_id, "departamento_id": departamento_id},
            "totais": totals, "itens": rows}


@router.get("/frota/custo-por-departamento", response_model=None)
def custo_por_departamento(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    departamento_id: int | None = None,
    export: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório de custo operacional de frota por departamento.

    Composição: abastecimento + serviço manutenção + peças/insumos do almoxarifado.
    Filtros: data_inicio, data_fim, departamento_id.
    Parâmetro export=csv retorna arquivo CSV.
    """
    ab_map = _ab_dept_agg(db, data_inicio, data_fim)
    man_map = _man_dept_agg(db, data_inicio, data_fim)
    pecas_map = _pecas_dept_agg(db, data_inicio, data_fim)

    # Collect all department IDs that appear in any source
    dept_ids: set[int | None] = (
        set(ab_map.keys()) | set(man_map.keys()) | set(pecas_map.keys())
    )
    if departamento_id is not None:
        dept_ids = {d for d in dept_ids if d == departamento_id}

    # Fetch department names
    depts = {d.id: d for d in db.query(Department).all()}

    rows = []
    for did in sorted(d for d in dept_ids if d is not None):
        ab = ab_map.get(did)
        man = man_map.get(did)
        pecas = pecas_map.get(did)
        custo_ab = round(float(ab.custo if ab else 0), 2)
        custo_man = round(float(man.custo if man else 0), 2)
        custo_pecas = round(float(pecas.custo if pecas else 0), 2)
        dept = depts.get(did)
        rows.append({
            "departamento_id": did,
            "departamento_nome": dept.name if dept else "—",
            "n_abastecimentos": int(ab.n if ab else 0),
            "total_litros": round(float(ab.litros if ab else 0), 2),
            "custo_abastecimento": custo_ab,
            "n_manutencoes": int(man.n if man else 0),
            "custo_manutencao_servico": custo_man,
            "n_pecas_almoxarifado": int(pecas.n if pecas else 0),
            "custo_pecas_almoxarifado": custo_pecas,
            "custo_total": round(custo_ab + custo_man + custo_pecas, 2),
        })

    # Also include "Sem departamento" bucket if there's data
    none_in_keys = None in (set(ab_map.keys()) | set(man_map.keys()) | set(pecas_map.keys()))
    if none_in_keys and departamento_id is None:
        ab_n = ab_map.get(None)
        man_n = man_map.get(None)
        pecas_n = pecas_map.get(None)
        custo_ab = round(float(ab_n.custo if ab_n else 0), 2)
        custo_man = round(float(man_n.custo if man_n else 0), 2)
        custo_pecas = round(float(pecas_n.custo if pecas_n else 0), 2)
        rows.append({
            "departamento_id": None,
            "departamento_nome": "Sem departamento",
            "n_abastecimentos": int(ab_n.n if ab_n else 0),
            "total_litros": round(float(ab_n.litros if ab_n else 0), 2),
            "custo_abastecimento": custo_ab,
            "n_manutencoes": int(man_n.n if man_n else 0),
            "custo_manutencao_servico": custo_man,
            "n_pecas_almoxarifado": int(pecas_n.n if pecas_n else 0),
            "custo_pecas_almoxarifado": custo_pecas,
            "custo_total": round(custo_ab + custo_man + custo_pecas, 2),
        })

    totals = {
        "total_departamentos": len(rows),
        "total_abastecimento": round(sum(r["custo_abastecimento"] for r in rows), 2),
        "total_manutencao_servico": round(sum(r["custo_manutencao_servico"] for r in rows), 2),
        "total_pecas_almoxarifado": round(sum(r["custo_pecas_almoxarifado"] for r in rows), 2),
        "total_geral": round(sum(r["custo_total"] for r in rows), 2),
    }

    if export == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "departamento_id", "departamento_nome",
            "n_abastecimentos", "total_litros", "custo_abastecimento",
            "n_manutencoes", "custo_manutencao_servico",
            "n_pecas_almoxarifado", "custo_pecas_almoxarifado", "custo_total",
        ])
        for r in rows:
            writer.writerow([
                r["departamento_id"], r["departamento_nome"],
                r["n_abastecimentos"], r["total_litros"], r["custo_abastecimento"],
                r["n_manutencoes"], r["custo_manutencao_servico"],
                r["n_pecas_almoxarifado"], r["custo_pecas_almoxarifado"], r["custo_total"],
            ])
        fname = "custo_por_departamento"
        if data_inicio:
            fname += f"_{data_inicio}"
        if data_fim:
            fname += f"_{data_fim}"
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={fname}.csv"},
        )

    return {"filtros": {"data_inicio": data_inicio, "data_fim": data_fim,
                        "departamento_id": departamento_id},
            "totais": totals, "itens": rows}
