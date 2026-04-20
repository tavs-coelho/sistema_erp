"""Router de Protocolo e Processos Administrativos."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Attachment, Protocolo, TramitacaoProtocolo, RoleEnum, User
from ..schemas import (
    ProtocoloCreate,
    ProtocoloOut,
    ProtocoloUpdate,
    TramitacaoCreate,
    TramitacaoOut,
)

router = APIRouter(prefix="/protocolo", tags=["protocolo"])

# Tipos de arquivo permitidos
ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}
MAX_UPLOAD_MB = 10


def _upload_dir() -> Path:
    """Return the upload directory, creating it on first use.

    Deferred to call time (rather than import time) to avoid side effects
    in restricted environments and to honour the centralised ``settings``
    value instead of reading the env-var directly.
    """
    d = Path(settings.upload_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d

# Status válidos para transições
VALID_TRANSITIONS: dict[str, list[str]] = {
    "protocolado":     ["em_tramitacao", "deferido", "indeferido", "arquivado"],
    "em_tramitacao":   ["deferido", "indeferido", "arquivado"],
    "deferido":        ["arquivado"],
    "indeferido":      ["arquivado"],
    "arquivado":       [],
}


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/protocolos")
def list_protocolos(
    status: str | None = None,
    tipo: str | None = None,
    prioridade: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Protocolo)
    if status:
        q = q.filter(Protocolo.status == status)
    if tipo:
        q = q.filter(Protocolo.tipo == tipo)
    if prioridade:
        q = q.filter(Protocolo.prioridade == prioridade)
    if search:
        q = q.filter(
            Protocolo.assunto.ilike(f"%{search}%")
            | Protocolo.interessado.ilike(f"%{search}%")
            | Protocolo.numero.ilike(f"%{search}%")
        )
    return _paginate(q.order_by(Protocolo.created_at.desc()), page, size)


@router.get("/protocolos/{protocolo_id}", response_model=ProtocoloOut)
def get_protocolo(protocolo_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return obj


@router.post("/protocolos", response_model=ProtocoloOut)
def create_protocolo(
    payload: ProtocoloCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if db.query(Protocolo).filter(Protocolo.numero == payload.numero).first():
        raise HTTPException(status_code=409, detail="Número de protocolo já existe")
    obj = Protocolo(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create",
        entity="protocolos", entity_id=str(obj.id),
        after_data={"numero": obj.numero, "tipo": obj.tipo, "assunto": obj.assunto},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/protocolos/{protocolo_id}", response_model=ProtocoloOut)
def update_protocolo(
    protocolo_id: int,
    payload: ProtocoloUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    before = {"status": obj.status, "assunto": obj.assunto}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    write_audit(
        db, user_id=current.id, action="update",
        entity="protocolos", entity_id=str(obj.id),
        before_data=before, after_data=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/protocolos/{protocolo_id}/tramitar", response_model=TramitacaoOut)
def tramitar_protocolo(
    protocolo_id: int,
    payload: TramitacaoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Tramita o protocolo para um novo departamento, registrando o despacho."""
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")

    # Calcula o novo status com base na ação
    ACAO_PARA_STATUS = {
        "encaminhado": "em_tramitacao",
        "deferido":    "deferido",
        "indeferido":  "indeferido",
        "arquivado":   "arquivado",
        "devolvido":   "em_tramitacao",
    }
    novo_status = ACAO_PARA_STATUS.get(payload.acao)
    if novo_status:
        allowed = VALID_TRANSITIONS.get(obj.status, [])
        if novo_status not in allowed and novo_status != obj.status:
            raise HTTPException(
                status_code=422,
                detail=f"Transição inválida: '{obj.status}' → '{novo_status}' (ação '{payload.acao}'). "
                       f"Transições válidas: {allowed}",
            )

    tram = TramitacaoProtocolo(
        protocolo_id=protocolo_id,
        de_department_id=obj.destino_department_id,
        para_department_id=payload.para_department_id,
        responsavel_id=current.id,
        acao=payload.acao,
        despacho=payload.despacho,
    )
    db.add(tram)

    # Atualiza status e destino do protocolo
    if novo_status:
        obj.status = novo_status
    obj.destino_department_id = payload.para_department_id

    db.flush()
    write_audit(
        db, user_id=current.id, action="update",
        entity="protocolos", entity_id=str(obj.id),
        after_data={"acao": payload.acao, "para_department": payload.para_department_id, "novo_status": obj.status},
    )
    db.commit()
    db.refresh(tram)
    return tram


@router.get("/protocolos/{protocolo_id}/tramitacoes", response_model=list[TramitacaoOut])
def list_tramitacoes(
    protocolo_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return db.query(TramitacaoProtocolo).filter(
        TramitacaoProtocolo.protocolo_id == protocolo_id
    ).order_by(TramitacaoProtocolo.created_at).all()


@router.get("/estatisticas")
def estatisticas(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Resumo quantitativo de protocolos por status."""
    from sqlalchemy import func
    rows = (
        db.query(Protocolo.status, func.count(Protocolo.id))
        .group_by(Protocolo.status)
        .all()
    )
    return {status: count for status, count in rows}


# ── GED — Anexos de Protocolo ─────────────────────────────────────────────────

@router.post("/protocolos/{protocolo_id}/anexos")
def upload_anexo(
    protocolo_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Faz upload de um arquivo e vincula ao protocolo.

    - Tamanho máximo: 10 MB
    - Tipos permitidos: PDF, JPEG, PNG, DOCX, DOC, TXT
    """
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de arquivo não permitido: {file.content_type}. "
                   f"Permitidos: {sorted(ALLOWED_MIME)}",
        )

    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Arquivo excede o limite de {MAX_UPLOAD_MB} MB")

    # Salva com nome único para evitar colisões
    ext = Path(file.filename or "file").suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = _upload_dir() / unique_name
    dest.write_bytes(contents)

    attachment = Attachment(
        entity_type="protocolo",
        entity_id=protocolo_id,
        file_name=file.filename or unique_name,
        path=str(dest),
    )
    db.add(attachment)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create",
        entity="attachments", entity_id=str(attachment.id),
        after_data={"protocolo_id": protocolo_id, "file_name": file.filename, "size_bytes": len(contents)},
    )
    db.commit()
    db.refresh(attachment)
    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "entity_type": attachment.entity_type,
        "entity_id": attachment.entity_id,
    }


@router.get("/protocolos/{protocolo_id}/anexos")
def list_anexos(
    protocolo_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista todos os anexos de um protocolo."""
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    anexos = (
        db.query(Attachment)
        .filter(Attachment.entity_type == "protocolo", Attachment.entity_id == protocolo_id)
        .all()
    )
    return [{"id": a.id, "file_name": a.file_name} for a in anexos]


@router.get("/anexos/{attachment_id}/download")
def download_anexo(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Faz download de um anexo pelo ID."""
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    if not Path(attachment.path).exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")
    return FileResponse(
        path=attachment.path,
        filename=attachment.file_name,
        media_type="application/octet-stream",
    )


@router.delete("/anexos/{attachment_id}", status_code=204)
def delete_anexo(
    attachment_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Remove um anexo (arquivo e registro no banco)."""
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    # Remove o arquivo do disco
    try:
        Path(attachment.path).unlink(missing_ok=True)
    except OSError:
        pass
    write_audit(
        db, user_id=current.id, action="delete",
        entity="attachments", entity_id=str(attachment_id),
        before_data={"file_name": attachment.file_name, "entity_id": attachment.entity_id},
    )
    db.delete(attachment)
    db.commit()
