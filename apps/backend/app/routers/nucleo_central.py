"""Service desk, internal notifications and practical self-service FAQ.

All notifications and conversations are tenant-and-user bound. The FAQ is a
curated guide for implemented actions, not a promise of regulatory conformity.
"""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, get_tenant_id, require_roles
from ..models import (
    MunicipalNotice, MunicipalSupportTicket, MunicipalSupportReply,
    RoleEnum, User, utc_now,
)

router = APIRouter(prefix="/nucleo/central", tags=["nucleo-central"])


FAQ = [
    {"topic": "Acesso", "question": "Como entrar no ERP?", "answer": "Acesse /login, informe usuário e senha institucionais. Se MFA estiver ativo, confirme no aplicativo autenticador."},
    {"topic": "Acesso", "question": "Esqueci minha senha. O que fazer?", "answer": "Use o fluxo de recuperação autorizado pela administração. O sistema não apresenta tokens de recuperação fora do modo demonstrativo."},
    {"topic": "Segurança", "question": "Como ativar o Google Authenticator?", "answer": "Abra Segurança da Conta, informe a senha atual, cadastre a chave no aplicativo e confirme o código TOTP de seis dígitos. Guarde os códigos de recuperação."},
    {"topic": "Segurança", "question": "Como encerrar sessões em outros dispositivos?", "answer": "Em Segurança da Conta, abra Dispositivos e Sessões e encerre a sessão desejada ou todas as sessões."},
    {"topic": "Unidades", "question": "Como registrar uma unidade municipal?", "answer": "Um administrador acessa Núcleo → Unidades, informa código e nome e seleciona secretaria pertencente à entidade."},
    {"topic": "Unidades", "question": "Por que não consigo selecionar um departamento?", "answer": "Somente departamentos ativos da mesma entidade podem ser associados a uma unidade."},
    {"topic": "Cadastros", "question": "Como cadastrar pessoa ou fornecedor?", "answer": "Abra Núcleo → Pessoas, selecione o tipo, informe nome e os contatos necessários. Perfis autorizados podem atualizar e desativar o cadastro."},
    {"topic": "Cadastros", "question": "Meu cadastro de fornecedor alimenta automaticamente compras?", "answer": "Ainda não. O diretório municipal é isolado; a integração com o módulo financeiro legado requer migração segura de dados."},
    {"topic": "Usuários", "question": "Como atribuir usuário a uma unidade?", "answer": "O administrador abre Núcleo → Lotações, seleciona usuário e unidade da mesma entidade e salva."},
    {"topic": "Usuários", "question": "A lotação altera o perfil do usuário?", "answer": "Não. A lotação registra vínculo organizacional, sem elevar permissões globais."},
    {"topic": "Documentos", "question": "Como criar e versionar documentos?", "answer": "Em Núcleo → Documentos, crie o registro; selecione-o na seção Versões, envie PDF/JPG/PNG/TXT até 8 MB e consulte as revisões."},
    {"topic": "Documentos", "question": "Quem vê documentos restritos?", "answer": "Somente o criador e administradores autorizados da mesma entidade; o acesso é revalidado no download."},
    {"topic": "Protocolo", "question": "Como registrar um protocolo?", "answer": "Abra Protocolo, informe assunto e interessado e deixe o número vazio para geração automática. Depois utilize Tramitar para registrar a movimentação."},
    {"topic": "Tarefas", "question": "Como atribuir e concluir uma tarefa?", "answer": "Abra Núcleo → Tarefas, escolha protocolo e responsável; o próprio responsável ou administrador pode iniciar e concluir."},
    {"topic": "Tarefas", "question": "Posso reabrir uma tarefa concluída?", "answer": "Não nesta versão; situações concluída ou cancelada são finais. Abra uma nova tarefa quando necessário."},
    {"topic": "Suporte", "question": "Como abrir um chamado?", "answer": "Abra Núcleo → Central, informe assunto, descrição e prioridade e acompanhe as respostas na mesma página."},
    {"topic": "Suporte", "question": "Quem pode consultar meu chamado?", "answer": "Você e administradores autorizados da sua entidade; chamados de outro município não são exibidos."},
    {"topic": "Operação", "question": "Como executar backup e restaurar?", "answer": "Use os scripts documentados em docs/operations/BACKUP-RESTORE.md. Restaurar é destrutivo e exige autorização e ambiente preparado."},
    {"topic": "Operação", "question": "Como identificar falhas do servidor?", "answer": "A equipe técnica pode consultar /health/live, /health/ready e os logs correlacionados por X-Request-ID."},
    {"topic": "Conformidade", "question": "O ERP já está homologado para o edital?", "answer": "Não. A cobertura por requisito e os testes da prova de conceito ainda exigem validação individual de cada módulo e requisito tecnológico."},
]


class NoticeOut(BaseModel):
    id: int
    kind: str
    title: str
    message: str
    reference_type: str | None
    reference_id: int | None
    created_at: datetime
    read_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: Literal["normal", "alta", "critica"] = "normal"


class TicketState(BaseModel):
    status: Literal["em_atendimento", "resolvido", "fechado"]


class ReplyCreate(BaseModel):
    message: str = Field(min_length=2, max_length=5000)


class TicketOut(BaseModel):
    id: int
    subject: str
    description: str
    priority: str
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReplyOut(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    message: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


def send_notice(db: Session, tenant: int, user_id: int, title: str,
                message: str, kind: str = "sistema",
                reference_type: str | None = None, reference_id: int | None = None):
    db.add(MunicipalNotice(
        tenant_id=tenant, user_id=user_id, title=title[:160],
        message=message[:500], kind=kind, reference_type=reference_type,
        reference_id=reference_id,
    ))


def _ticket(db: Session, tenant: int, ticket_id: int, current: User):
    ticket = db.query(MunicipalSupportTicket).filter(
        MunicipalSupportTicket.id == ticket_id,
        MunicipalSupportTicket.tenant_id == tenant,
    ).first()
    if ticket is None or (current.role != RoleEnum.admin and ticket.created_by != current.id):
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    return ticket


def _notify_admins(db: Session, tenant: int, ticket_id: int):
    q = db.query(User).filter(User.role == RoleEnum.admin, User.active.is_(True))
    q = q.filter(or_(User.tenant_id == 1, User.tenant_id.is_(None))
                 if tenant == 1 else User.tenant_id == tenant)
    for admin in q.limit(25).all():
        send_notice(db, tenant, admin.id, "Chamado atualizado",
                    f"O chamado #{ticket_id} recebeu uma atualização.",
                    "chamado", "support_ticket", ticket_id)


@router.get("/faq")
def faq(_: User = Depends(get_current_user)):
    return FAQ


@router.get("/notificacoes", response_model=list[NoticeOut])
def my_notices(unread: bool = False, db: Session = Depends(get_db),
               tenant: int = Depends(get_tenant_id),
               current: User = Depends(get_current_user)):
    q = db.query(MunicipalNotice).filter(
        MunicipalNotice.tenant_id == tenant, MunicipalNotice.user_id == current.id,
    )
    if unread:
        q = q.filter(MunicipalNotice.read_at.is_(None))
    return q.order_by(MunicipalNotice.id.desc()).limit(100).all()


@router.patch("/notificacoes/{notice_id}/ler", response_model=NoticeOut)
def read_notice(notice_id: int, db: Session = Depends(get_db),
                tenant: int = Depends(get_tenant_id),
                current: User = Depends(get_current_user)):
    item = db.query(MunicipalNotice).filter(
        MunicipalNotice.id == notice_id,
        MunicipalNotice.tenant_id == tenant,
        MunicipalNotice.user_id == current.id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    if item.read_at is None:
        item.read_at = utc_now()
        db.commit()
        db.refresh(item)
    return item


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                 current: User = Depends(get_current_user)):
    q = db.query(MunicipalSupportTicket).filter(MunicipalSupportTicket.tenant_id == tenant)
    if current.role != RoleEnum.admin:
        q = q.filter(MunicipalSupportTicket.created_by == current.id)
    return q.order_by(MunicipalSupportTicket.id.desc()).limit(100).all()


@router.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db),
                  tenant: int = Depends(get_tenant_id),
                  current: User = Depends(get_current_user)):
    item = MunicipalSupportTicket(
        tenant_id=tenant, created_by=current.id,
        subject=payload.subject.strip(), description=payload.description.strip(),
        priority=payload.priority,
    )
    db.add(item)
    db.flush()
    _notify_admins(db, tenant, item.id)
    write_audit(db, user_id=current.id, action="create", entity="municipal_support_tickets",
                entity_id=str(item.id), after_data={"tenant_id": tenant, "priority": item.priority})
    db.commit()
    db.refresh(item)
    return item


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db),
               tenant: int = Depends(get_tenant_id),
               current: User = Depends(get_current_user)):
    return _ticket(db, tenant, ticket_id, current)


@router.get("/tickets/{ticket_id}/respostas", response_model=list[ReplyOut])
def list_replies(ticket_id: int, db: Session = Depends(get_db),
                 tenant: int = Depends(get_tenant_id),
                 current: User = Depends(get_current_user)):
    _ticket(db, tenant, ticket_id, current)
    return db.query(MunicipalSupportReply).filter(
        MunicipalSupportReply.tenant_id == tenant,
        MunicipalSupportReply.ticket_id == ticket_id,
    ).order_by(MunicipalSupportReply.id).all()


@router.post("/tickets/{ticket_id}/respostas", response_model=ReplyOut, status_code=201)
def add_reply(ticket_id: int, payload: ReplyCreate, db: Session = Depends(get_db),
              tenant: int = Depends(get_tenant_id),
              current: User = Depends(get_current_user)):
    item = _ticket(db, tenant, ticket_id, current)
    if item.status == "fechado":
        raise HTTPException(status_code=409, detail="Chamado encerrado")
    reply = MunicipalSupportReply(
        tenant_id=tenant, ticket_id=ticket_id,
        author_id=current.id, message=payload.message.strip(),
    )
    db.add(reply)
    db.flush()
    if current.id != item.created_by:
        send_notice(db, tenant, item.created_by, "Resposta do suporte",
                    f"Seu chamado #{ticket_id} recebeu uma resposta.",
                    "chamado", "support_ticket", ticket_id)
    else:
        _notify_admins(db, tenant, ticket_id)
    write_audit(db, user_id=current.id, action="reply", entity="municipal_support_tickets",
                entity_id=str(ticket_id), after_data={"tenant_id": tenant, "reply_id": reply.id})
    db.commit()
    db.refresh(reply)
    return reply


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
def set_ticket_state(ticket_id: int, payload: TicketState,
                     db: Session = Depends(get_db), tenant: int = Depends(get_tenant_id),
                     current: User = Depends(require_roles(RoleEnum.admin))):
    item = _ticket(db, tenant, ticket_id, current)
    if item.status == "fechado":
        raise HTTPException(status_code=409, detail="Chamado já fechado")
    old = item.status
    item.status = payload.status
    if item.created_by != current.id:
        send_notice(db, tenant, item.created_by, "Situação do suporte atualizada",
                    f"Seu chamado #{item.id} mudou para {payload.status}.",
                    "chamado", "support_ticket", item.id)
    write_audit(db, user_id=current.id, action="status", entity="municipal_support_tickets",
                entity_id=str(item.id), before_data={"status": old},
                after_data={"tenant_id": tenant, "status": payload.status})
    db.commit()
    db.refresh(item)
    return item
