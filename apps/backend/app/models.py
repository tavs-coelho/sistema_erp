from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utc_now():
    return datetime.now(timezone.utc)


class RoleEnum(str, Enum):
    admin = "admin"
    accountant = "accountant"
    hr = "hr"
    procurement = "procurement"
    patrimony = "patrimony"
    employee = "employee"
    read_only = "read_only"


class Municipality(Base):
    __tablename__ = "municipalities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class FiscalYear(Base):
    __tablename__ = "fiscal_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    cpf: Mapped[str] = mapped_column(String(14), unique=True)
    job_title: Mapped[str] = mapped_column(String(120))
    employment_type: Mapped[str] = mapped_column(String(60), default="Efetivo")
    base_salary: Mapped[float] = mapped_column(Float)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    department = relationship("Department")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(SqlEnum(RoleEnum), index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    document: Mapped[str] = mapped_column(String(20), unique=True)


class BudgetAllocation(Base):
    __tablename__ = "budget_allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    fiscal_year_id: Mapped[int] = mapped_column(ForeignKey("fiscal_years.id"))


class FundingSource(Base):
    __tablename__ = "funding_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class Commitment(Base):
    __tablename__ = "commitments"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="empenhado")
    fiscal_year_id: Mapped[int] = mapped_column(ForeignKey("fiscal_years.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))


class Liquidation(Base):
    __tablename__ = "liquidations"
    id: Mapped[int] = mapped_column(primary_key=True)
    commitment_id: Mapped[int] = mapped_column(ForeignKey("commitments.id"))
    amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    commitment_id: Mapped[int] = mapped_column(ForeignKey("commitments.id"))
    amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[date] = mapped_column(Date)


class RevenueEntry(Base):
    __tablename__ = "revenue_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    entry_date: Mapped[date] = mapped_column(Date)


class ProcurementProcess(Base):
    __tablename__ = "procurement_processes"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    object_description: Mapped[str] = mapped_column(String(220))
    status: Mapped[str] = mapped_column(String(40), default="aberto")


class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("procurement_processes.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="vigente")


class ContractAddendum(Base):
    __tablename__ = "contract_addenda"
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    description: Mapped[str] = mapped_column(String(220))
    amount_delta: Mapped[float] = mapped_column(Float)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(String(200))
    classification: Mapped[str] = mapped_column(String(80))
    location: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    responsible_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    value: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="ativo")


class AssetMovement(Base):
    __tablename__ = "asset_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    from_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    to_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(40))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PayrollEvent(Base):
    __tablename__ = "payroll_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    month: Mapped[str] = mapped_column(String(7), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(120))
    value: Mapped[float] = mapped_column(Float)


class Payslip(Base):
    __tablename__ = "payslips"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    month: Mapped[str] = mapped_column(String(7), index=True)
    gross_amount: Mapped[float] = mapped_column(Float)
    deductions: Mapped[float] = mapped_column(Float)
    net_amount: Mapped[float] = mapped_column(Float)


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    file_name: Mapped[str] = mapped_column(String(160))
    path: Mapped[str] = mapped_column(String(255))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(20))
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(40))
    before_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(120), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


# ── Protocolo / Processos Administrativos ────────────────────────────────────

class Protocolo(Base):
    """Protocolo de entrada de processo administrativo."""
    __tablename__ = "protocolos"
    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(60))          # requerimento, oficio, recurso, etc.
    assunto: Mapped[str] = mapped_column(String(255))
    interessado: Mapped[str] = mapped_column(String(160))  # nome do solicitante/interessado
    interessado_doc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    origem_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    destino_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="protocolado")   # protocolado, em_tramitacao, deferido, indeferido, arquivado
    prioridade: Mapped[str] = mapped_column(String(20), default="normal")    # normal, urgente, sigiloso
    data_entrada: Mapped[date] = mapped_column(Date)
    prazo: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    tramitacoes = relationship("TramitacaoProtocolo", back_populates="protocolo", cascade="all, delete-orphan", order_by="TramitacaoProtocolo.created_at")
    origem_department = relationship("Department", foreign_keys=[origem_department_id])
    destino_department = relationship("Department", foreign_keys=[destino_department_id])


class TramitacaoProtocolo(Base):
    """Registro de movimentação/tramitação de um protocolo entre departamentos."""
    __tablename__ = "tramitacoes_protocolo"
    id: Mapped[int] = mapped_column(primary_key=True)
    protocolo_id: Mapped[int] = mapped_column(ForeignKey("protocolos.id"))
    de_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    para_department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    responsavel_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acao: Mapped[str] = mapped_column(String(60))          # encaminhado, deferido, indeferido, arquivado, devolvido
    despacho: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    protocolo = relationship("Protocolo", back_populates="tramitacoes")
    para_department = relationship("Department", foreign_keys=[para_department_id])


# ── Convênios ─────────────────────────────────────────────────────────────────

class Convenio(Base):
    """Convênio firmado com entidade concedente ou convenente."""
    __tablename__ = "convenios"
    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    objeto: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(30), default="recebimento")   # recebimento, repasse
    concedente: Mapped[str] = mapped_column(String(160))    # nome da entidade/órgão concedente
    cnpj_concedente: Mapped[str | None] = mapped_column(String(18), nullable=True)
    valor_total: Mapped[float] = mapped_column(Float, default=0.0)
    contrapartida: Mapped[float] = mapped_column(Float, default=0.0)
    data_assinatura: Mapped[date] = mapped_column(Date)
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="vigente")     # rascunho, vigente, encerrado, suspenso, rescindido
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    loa_item_id: Mapped[int | None] = mapped_column(ForeignKey("loa_items.id"), nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    desembolsos = relationship("ConvenioDesembolso", back_populates="convenio", cascade="all, delete-orphan")
    department = relationship("Department", foreign_keys=[department_id])


class ConvenioDesembolso(Base):
    """Registro de desembolso (parcela liberada) de um convênio."""
    __tablename__ = "convenio_desembolsos"
    id: Mapped[int] = mapped_column(primary_key=True)
    convenio_id: Mapped[int] = mapped_column(ForeignKey("convenios.id"))
    numero_parcela: Mapped[int] = mapped_column(Integer)
    valor: Mapped[float] = mapped_column(Float)
    data_prevista: Mapped[date] = mapped_column(Date)
    data_efetiva: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="previsto")    # previsto, recebido, pendente
    observacoes: Mapped[str] = mapped_column(Text, default="")
    convenio = relationship("Convenio", back_populates="desembolsos")


# ── Tributário / Arrecadação Municipal ───────────────────────────────────────

class Contribuinte(Base):
    """Contribuinte municipal (pessoa física ou jurídica)."""
    __tablename__ = "contribuintes"
    id: Mapped[int] = mapped_column(primary_key=True)
    cpf_cnpj: Mapped[str] = mapped_column(String(18), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(160))
    tipo: Mapped[str] = mapped_column(String(2), default="PF")          # PF | PJ
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    logradouro: Mapped[str] = mapped_column(String(200), default="")
    numero: Mapped[str] = mapped_column(String(10), default="")
    complemento: Mapped[str] = mapped_column(String(80), default="")
    bairro: Mapped[str] = mapped_column(String(80), default="")
    municipio: Mapped[str] = mapped_column(String(80), default="")
    uf: Mapped[str] = mapped_column(String(2), default="")
    cep: Mapped[str] = mapped_column(String(9), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    imoveis = relationship("ImovelCadastral", back_populates="contribuinte", cascade="all, delete-orphan")
    lancamentos = relationship("LancamentoTributario", back_populates="contribuinte")


class ImovelCadastral(Base):
    """Cadastro imobiliário simplificado para fins de IPTU/ITBI."""
    __tablename__ = "imoveis_cadastrais"
    id: Mapped[int] = mapped_column(primary_key=True)
    inscricao: Mapped[str] = mapped_column(String(30), unique=True, index=True)   # inscrição cadastral
    contribuinte_id: Mapped[int] = mapped_column(ForeignKey("contribuintes.id"))
    logradouro: Mapped[str] = mapped_column(String(200))
    numero: Mapped[str] = mapped_column(String(10), default="")
    complemento: Mapped[str] = mapped_column(String(80), default="")
    bairro: Mapped[str] = mapped_column(String(80), default="")
    area_terreno: Mapped[float] = mapped_column(Float, default=0.0)                # m²
    area_construida: Mapped[float] = mapped_column(Float, default=0.0)             # m²
    valor_venal: Mapped[float] = mapped_column(Float, default=0.0)                 # R$
    uso: Mapped[str] = mapped_column(String(30), default="residencial")            # residencial, comercial, industrial, rural
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    contribuinte = relationship("Contribuinte", back_populates="imoveis")
    lancamentos = relationship("LancamentoTributario", back_populates="imovel")


class LancamentoTributario(Base):
    """Lançamento de tributo (IPTU, ISS, ITBI, taxas) para um contribuinte/imóvel."""
    __tablename__ = "lancamentos_tributarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    contribuinte_id: Mapped[int] = mapped_column(ForeignKey("contribuintes.id"))
    imovel_id: Mapped[int | None] = mapped_column(ForeignKey("imoveis_cadastrais.id"), nullable=True)
    tributo: Mapped[str] = mapped_column(String(20))        # IPTU, ISS, ITBI, TAXA_LIXO, TAXA_ILUMINACAO, etc.
    competencia: Mapped[str] = mapped_column(String(7))     # YYYY-MM  (ex: 2026-01)
    exercicio: Mapped[int] = mapped_column(Integer)         # ano de referência
    valor_principal: Mapped[float] = mapped_column(Float)
    valor_juros: Mapped[float] = mapped_column(Float, default=0.0)
    valor_multa: Mapped[float] = mapped_column(Float, default=0.0)
    valor_desconto: Mapped[float] = mapped_column(Float, default=0.0)
    valor_total: Mapped[float] = mapped_column(Float)       # calculado ao criar/atualizar
    vencimento: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="aberto")   # aberto, pago, cancelado, inscrito_divida
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    contribuinte = relationship("Contribuinte", back_populates="lancamentos")
    imovel = relationship("ImovelCadastral", back_populates="lancamentos")
    guias = relationship("GuiaPagamento", back_populates="lancamento", cascade="all, delete-orphan")


class GuiaPagamento(Base):
    """Guia de arrecadação gerada a partir de um lançamento tributário."""
    __tablename__ = "guias_pagamento"
    id: Mapped[int] = mapped_column(primary_key=True)
    lancamento_id: Mapped[int] = mapped_column(ForeignKey("lancamentos_tributarios.id"))
    codigo_barras: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    valor: Mapped[float] = mapped_column(Float)
    vencimento: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="emitida")   # emitida, paga, cancelada, vencida
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    banco: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    lancamento = relationship("LancamentoTributario", back_populates="guias")


class DividaAtiva(Base):
    """Inscrição de crédito tributário em dívida ativa municipal."""
    __tablename__ = "divida_ativa"
    id: Mapped[int] = mapped_column(primary_key=True)
    lancamento_id: Mapped[int] = mapped_column(ForeignKey("lancamentos_tributarios.id"), unique=True)
    contribuinte_id: Mapped[int] = mapped_column(ForeignKey("contribuintes.id"))
    numero_inscricao: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    tributo: Mapped[str] = mapped_column(String(20))
    exercicio: Mapped[int] = mapped_column(Integer)
    valor_original: Mapped[float] = mapped_column(Float)
    valor_atualizado: Mapped[float] = mapped_column(Float)       # com correção e juros de mora
    data_inscricao: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="ativa")   # ativa, quitada, parcelada, ajuizada, prescrita
    data_ajuizamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    lancamento = relationship("LancamentoTributario")
    contribuinte = relationship("Contribuinte")
    parcelas = relationship("ParcelaDivida", back_populates="divida", cascade="all, delete-orphan", order_by="ParcelaDivida.numero_parcela")


class ParcelamentoDivida(Base):
    """Acordo de parcelamento de dívida ativa."""
    __tablename__ = "parcelamentos_divida"
    id: Mapped[int] = mapped_column(primary_key=True)
    divida_id: Mapped[int] = mapped_column(ForeignKey("divida_ativa.id"))
    numero_parcelas: Mapped[int] = mapped_column(Integer)
    valor_total: Mapped[float] = mapped_column(Float)       # valor acordado total (pode incluir desconto de mora)
    data_acordo: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="ativo")    # ativo, quitado, cancelado, inadimplente
    observacoes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    divida = relationship("DividaAtiva", foreign_keys=[divida_id])
    parcelas = relationship("ParcelaDivida", back_populates="parcelamento", cascade="all, delete-orphan", order_by="ParcelaDivida.numero_parcela")


class ParcelaDivida(Base):
    """Parcela individual de um parcelamento de dívida ativa."""
    __tablename__ = "parcelas_divida"
    id: Mapped[int] = mapped_column(primary_key=True)
    parcelamento_id: Mapped[int] = mapped_column(ForeignKey("parcelamentos_divida.id"))
    divida_id: Mapped[int] = mapped_column(ForeignKey("divida_ativa.id"))
    numero_parcela: Mapped[int] = mapped_column(Integer)
    valor: Mapped[float] = mapped_column(Float)
    vencimento: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="aberta")   # aberta, paga, vencida, cancelada
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    parcelamento = relationship("ParcelamentoDivida", back_populates="parcelas")
    divida = relationship("DividaAtiva", foreign_keys=[divida_id], back_populates="parcelas")


class AliquotaIPTU(Base):
    """Tabela de alíquotas de IPTU por uso do imóvel e exercício fiscal."""
    __tablename__ = "aliquotas_iptu"
    id: Mapped[int] = mapped_column(primary_key=True)
    exercicio: Mapped[int] = mapped_column(Integer, index=True)         # ano de vigência
    uso: Mapped[str] = mapped_column(String(30))                        # residencial, comercial, industrial, rural
    aliquota: Mapped[float] = mapped_column(Float)                      # ex: 0.005 = 0.5%
    descricao: Mapped[str] = mapped_column(String(120), default="")


# ── Módulo orçamentário: PPA / LDO / LOA ─────────────────────────────────────

class PPA(Base):
    """Plano Plurianual — vigência de 4 anos."""
    __tablename__ = "ppas"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_start: Mapped[int] = mapped_column(Integer)
    period_end: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="rascunho")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    programs = relationship("PPAProgram", back_populates="ppa", cascade="all, delete-orphan")


class PPAProgram(Base):
    """Programa de governo dentro do PPA."""
    __tablename__ = "ppa_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ppa_id: Mapped[int] = mapped_column(ForeignKey("ppas.id"))
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str] = mapped_column(Text, default="")
    estimated_amount: Mapped[float] = mapped_column(Float, default=0.0)
    ppa = relationship("PPA", back_populates="programs")


class LDO(Base):
    """Lei de Diretrizes Orçamentárias — por exercício."""
    __tablename__ = "ldos"
    id: Mapped[int] = mapped_column(primary_key=True)
    fiscal_year_id: Mapped[int] = mapped_column(ForeignKey("fiscal_years.id"))
    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="rascunho")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    goals = relationship("LDOGoal", back_populates="ldo", cascade="all, delete-orphan")


class LDOGoal(Base):
    """Meta/diretriz dentro da LDO."""
    __tablename__ = "ldo_goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    ldo_id: Mapped[int] = mapped_column(ForeignKey("ldos.id"))
    code: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(60), default="prioridade")
    ldo = relationship("LDO", back_populates="goals")


class LOA(Base):
    """Lei Orçamentária Anual — orçamento aprovado para o exercício."""
    __tablename__ = "loas"
    id: Mapped[int] = mapped_column(primary_key=True)
    fiscal_year_id: Mapped[int] = mapped_column(ForeignKey("fiscal_years.id"))
    ldo_id: Mapped[int | None] = mapped_column(ForeignKey("ldos.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    total_expenditure: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="rascunho")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    items = relationship("LOAItem", back_populates="loa", cascade="all, delete-orphan")


class LOAItem(Base):
    """Dotação unitária dentro da LOA (função/subfunção/programa/ação)."""
    __tablename__ = "loa_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    loa_id: Mapped[int] = mapped_column(ForeignKey("loas.id"))
    function_code: Mapped[str] = mapped_column(String(10))
    subfunction_code: Mapped[str] = mapped_column(String(10))
    program_code: Mapped[str] = mapped_column(String(20))
    action_code: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(30), default="despesa")
    authorized_amount: Mapped[float] = mapped_column(Float)
    executed_amount: Mapped[float] = mapped_column(Float, default=0.0)
    loa = relationship("LOA", back_populates="items")
