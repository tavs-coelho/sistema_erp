"""Router SICONFI Onda 19 — Geração de XML e Envio Real.

Fase 1 (implementada aqui):
  - Geração de XML para FINBRA / RREO / RGF a partir dos payloads JSON da Onda 18
  - Validação local contra XSD inline (aproximação do layout Tesouro Nacional)
  - Download do XML gerado (application/xml)
  - Log de cada validação (ValidacaoXmlLog)
  - Histórico de validações com filtros

Fase 2 (stub — retorna 501 Not Implemented):
  - POST /siconfi/envio — prepara envio real via webservice SICONFI
    * suporte a certificado digital A1 (PFX/base64)
    * dry_run mode (simula sem postar)
    * log completo de protocolo, retorno, reprocessamento

LIMITAÇÕES CONHECIDAS (Fase 1):
  * O XSD utilizado é inline e aproximado — não garante compatibilidade
    total com o webservice do Tesouro Nacional.
  * Não há assinatura digital WS-Security no XML — obrigatória para envio real.
  * Conversão JSON→XML segue nomenclatura própria; pode precisar de ajuste
    fino ao implementar a Fase 2 com o WSDL oficial.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    ConfiguracaoEntidade,
    EnvioSiconfiLog,
    FiscalYear,
    RoleEnum,
    User,
    ValidacaoXmlLog,
)
from ..schemas import (
    EnvioSiconfiOut,
    EnvioSiconfiRequest,
    ValidacaoXmlOut,
    ValidacaoXmlRequest,
)
from ..siconfi_xml import (
    build_xml_finbra,
    build_xml_rgf,
    build_xml_rreo,
    validate_xml,
    xml_bytes_to_str,
)
from .siconfi_siop import (
    _build_finbra,
    _build_rgf_estruturado,
    _build_rreo_estruturado,
    _fy,
)

router = APIRouter(prefix="/siconfi", tags=["siconfi-xml"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg_dict(db: Session) -> dict:
    """Retorna dicionário com dados da entidade ativa (ou defaults vazios)."""
    cfg = db.query(ConfiguracaoEntidade).filter_by(ativo=True).first()
    if cfg:
        return {
            "nome_entidade": cfg.nome_entidade,
            "cnpj": cfg.cnpj,
            "codigo_ibge": cfg.codigo_ibge,
            "uf": cfg.uf,
            "esfera": cfg.esfera,
            "poder": cfg.poder,
            "responsavel_nome": cfg.responsavel_nome,
            "responsavel_cargo": cfg.responsavel_cargo,
            "responsavel_cpf": cfg.responsavel_cpf,
        }
    return {}


def _bimestre_atual() -> int:
    return min(6, (date.today().month - 1) // 2 + 1)


def _quadrimestre_atual() -> int:
    return min(3, (date.today().month - 1) // 4 + 1)


def _save_validacao(
    db: Session,
    tipo: str,
    exercicio: int,
    periodo: str | None,
    valido: bool,
    erros: list[str],
    avisos: list[str],
    xml_bytes: bytes,
    user_id: int | None,
) -> ValidacaoXmlLog:
    log = ValidacaoXmlLog(
        tipo=tipo,
        exercicio=exercicio,
        periodo=periodo,
        valido=valido,
        erros_xsd=erros if erros else [],
        avisos=avisos,
        xml_gerado=xml_bytes_to_str(xml_bytes),
        xsd_fonte="inline",
        gerado_por_id=user_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ── Geração + Validação FINBRA ────────────────────────────────────────────────

@router.get("/xml/finbra")
def xml_finbra(
    exercicio: int = Query(default=None),
    download: bool = Query(default=False, description="Se True retorna application/xml para download"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Gera e valida XML FINBRA. Retorna JSON de resultado ou arquivo XML."""
    if not exercicio:
        exercicio = date.today().year
    if not _fy(db, exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {exercicio} não encontrado")

    payload = _build_finbra(db, exercicio)
    cfg = _cfg_dict(db)
    xml_bytes = build_xml_finbra(payload, cfg)
    valido, erros, avisos = validate_xml(xml_bytes, "finbra")

    log = _save_validacao(db, "finbra", exercicio, "ANUAL", valido, erros, avisos, xml_bytes, current.id)
    write_audit(db, user_id=current.id, action="create", entity="validacoes_xml_siconfi",
                entity_id=str(log.id),
                after_data={"tipo": "finbra", "exercicio": exercicio, "valido": valido})

    if download:
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=finbra_{exercicio}.xml"},
        )

    return {
        "validacao_id": log.id,
        "tipo": "finbra",
        "exercicio": exercicio,
        "valido": valido,
        "erros_xsd": erros,
        "avisos": avisos,
        "xml_tamanho_bytes": len(xml_bytes),
        "xml_preview": xml_bytes.decode("utf-8")[:2000],
    }


# ── Geração + Validação RREO ──────────────────────────────────────────────────

@router.get("/xml/rreo")
def xml_rreo(
    exercicio: int = Query(default=None),
    bimestre: int = Query(default=None, ge=1, le=6),
    download: bool = Query(default=False),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Gera e valida XML RREO bimestral."""
    hoje = date.today()
    if not exercicio:
        exercicio = hoje.year
    if not bimestre:
        bimestre = _bimestre_atual()
    if not _fy(db, exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {exercicio} não encontrado")

    payload = _build_rreo_estruturado(db, exercicio, bimestre)
    cfg = _cfg_dict(db)
    xml_bytes = build_xml_rreo(payload, cfg)
    valido, erros, avisos = validate_xml(xml_bytes, "rreo")
    periodo = f"bimestre_{bimestre}"

    log = _save_validacao(db, "rreo", exercicio, periodo, valido, erros, avisos, xml_bytes, current.id)
    write_audit(db, user_id=current.id, action="create", entity="validacoes_xml_siconfi",
                entity_id=str(log.id),
                after_data={"tipo": "rreo", "exercicio": exercicio, "bimestre": bimestre, "valido": valido})

    if download:
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=rreo_{exercicio}_bim{bimestre}.xml"},
        )

    return {
        "validacao_id": log.id,
        "tipo": "rreo",
        "exercicio": exercicio,
        "bimestre": bimestre,
        "valido": valido,
        "erros_xsd": erros,
        "avisos": avisos,
        "xml_tamanho_bytes": len(xml_bytes),
        "xml_preview": xml_bytes.decode("utf-8")[:2000],
    }


# ── Geração + Validação RGF ───────────────────────────────────────────────────

@router.get("/xml/rgf")
def xml_rgf(
    exercicio: int = Query(default=None),
    quadrimestre: int = Query(default=None, ge=1, le=3),
    download: bool = Query(default=False),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Gera e valida XML RGF quadrimestral."""
    hoje = date.today()
    if not exercicio:
        exercicio = hoje.year
    if not quadrimestre:
        quadrimestre = _quadrimestre_atual()
    if not _fy(db, exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {exercicio} não encontrado")

    payload = _build_rgf_estruturado(db, exercicio, quadrimestre)
    cfg = _cfg_dict(db)
    xml_bytes = build_xml_rgf(payload, cfg)
    valido, erros, avisos = validate_xml(xml_bytes, "rgf")
    periodo = f"quad_{quadrimestre}"

    log = _save_validacao(db, "rgf", exercicio, periodo, valido, erros, avisos, xml_bytes, current.id)
    write_audit(db, user_id=current.id, action="create", entity="validacoes_xml_siconfi",
                entity_id=str(log.id),
                after_data={"tipo": "rgf", "exercicio": exercicio, "quadrimestre": quadrimestre, "valido": valido})

    if download:
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=rgf_{exercicio}_quad{quadrimestre}.xml"},
        )

    return {
        "validacao_id": log.id,
        "tipo": "rgf",
        "exercicio": exercicio,
        "quadrimestre": quadrimestre,
        "valido": valido,
        "erros_xsd": erros,
        "avisos": avisos,
        "xml_tamanho_bytes": len(xml_bytes),
        "xml_preview": xml_bytes.decode("utf-8")[:2000],
    }


# ── Validação avulsa ──────────────────────────────────────────────────────────

@router.post("/xml/validar", response_model=ValidacaoXmlOut)
def validar_xml(
    payload: ValidacaoXmlRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Gera e valida XML para o tipo/período informado. Registra no log."""
    if not _fy(db, payload.exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {payload.exercicio} não encontrado")

    cfg = _cfg_dict(db)
    periodo = payload.periodo or "ANUAL"

    if payload.tipo == "finbra":
        data = _build_finbra(db, payload.exercicio)
        xml_bytes = build_xml_finbra(data, cfg)
    elif payload.tipo == "rreo":
        bim = int(periodo.split("_")[-1]) if "_" in periodo else _bimestre_atual()
        bim = max(1, min(6, bim))
        data = _build_rreo_estruturado(db, payload.exercicio, bim)
        xml_bytes = build_xml_rreo(data, cfg)
    elif payload.tipo == "rgf":
        quad = int(periodo.split("_")[-1]) if "_" in periodo else _quadrimestre_atual()
        quad = max(1, min(3, quad))
        data = _build_rgf_estruturado(db, payload.exercicio, quad)
        xml_bytes = build_xml_rgf(data, cfg)
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo '{payload.tipo}' inválido. Use: finbra, rreo, rgf",
        )

    valido, erros, avisos = validate_xml(xml_bytes, payload.tipo)
    log = _save_validacao(
        db, payload.tipo, payload.exercicio, periodo,
        valido, erros, avisos, xml_bytes, current.id
    )
    return log


# ── Download de XML de uma validação salva ────────────────────────────────────

@router.get("/xml/{validacao_id}/download")
def download_xml(
    validacao_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Faz download do XML salvo em uma validação específica."""
    log = db.get(ValidacaoXmlLog, validacao_id)
    if not log:
        raise HTTPException(status_code=404, detail="Validação não encontrada")
    if not log.xml_gerado:
        raise HTTPException(status_code=404, detail="XML não disponível para esta validação")
    xml_bytes = log.xml_gerado.encode("utf-8")
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={log.tipo}_{log.exercicio}_{log.id}.xml"},
    )


# ── Histórico de validações ───────────────────────────────────────────────────

@router.get("/xml/historico")
def historico_validacoes(
    exercicio: int | None = None,
    tipo: str | None = None,
    valido: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista histórico de validações XML com filtros."""
    q = db.query(ValidacaoXmlLog)
    if exercicio:
        q = q.filter(ValidacaoXmlLog.exercicio == exercicio)
    if tipo:
        q = q.filter(ValidacaoXmlLog.tipo == tipo)
    if valido is not None:
        q = q.filter(ValidacaoXmlLog.valido == valido)
    total = q.count()
    items = q.order_by(ValidacaoXmlLog.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": i.id,
                "tipo": i.tipo,
                "exercicio": i.exercicio,
                "periodo": i.periodo,
                "valido": i.valido,
                "erros_xsd": i.erros_xsd,
                "avisos": i.avisos,
                "xsd_fonte": i.xsd_fonte,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ],
    }


# ── Fase 2 — Envio Real (STUB) ────────────────────────────────────────────────

@router.post("/envio", response_model=None, status_code=501)
def envio_siconfi(
    payload: EnvioSiconfiRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin)),
):
    """[FASE 2 — NÃO IMPLEMENTADO] Envia XML ao webservice SICONFI com certificado digital A1.

    Esta rota é um stub que documenta o contrato de Fase 2:
      - Carrega certificado PFX (base64) e assina o XML com WS-Security
      - Posta no endpoint SOAP do Tesouro Nacional
      - Registra protocolo, retorno, erros e reprocessamento no log

    Status: 501 Not Implemented — aguardando:
      1. Credenciais SICONFI (usuário gov.br)
      2. Certificado ICP-Brasil A1/A3 do gestor
      3. WSDL oficial do webservice SICONFI
      4. Biblioteca de assinatura XML (signxml ou lxml-c14n)
    """
    return {
        "detail": "Fase 2 não implementada. Veja docs/siconfi-onda19.md para o roadmap de envio real.",
        "status": "NOT_IMPLEMENTED",
        "fase": 2,
        "requisitos_pendentes": [
            "Credenciais gov.br (usuário SICONFI)",
            "Certificado ICP-Brasil A1/A3 do responsável",
            "WSDL do webservice SICONFI Tesouro Nacional",
            "Biblioteca de assinatura XML WS-Security (signxml)",
            "Mapeamento JSON→XSD validado pelo Tesouro Nacional",
        ],
        "dry_run_solicitado": payload.dry_run,
        "validacao_xml_id": payload.validacao_xml_id,
    }


@router.get("/envio/historico")
def historico_envios(
    exercicio: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista histórico de envios (Fase 2 — sempre vazio até implementação real)."""
    q = db.query(EnvioSiconfiLog)
    if exercicio:
        q = q.filter(EnvioSiconfiLog.exercicio == exercicio)
    if status:
        q = q.filter(EnvioSiconfiLog.status == status)
    total = q.count()
    items = q.order_by(EnvioSiconfiLog.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "nota": "Envio real (Fase 2) não implementado — todos os registros aqui são de testes.",
        "items": [],
    }
