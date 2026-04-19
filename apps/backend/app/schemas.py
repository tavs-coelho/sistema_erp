from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr

from .models import RoleEnum


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: RoleEnum
    must_change_password: bool


class AuthMeResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: RoleEnum
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    new_password: str


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    role: RoleEnum
    password: str
    employee_id: int | None = None


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    role: RoleEnum
    active: bool

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str


class DepartmentOut(BaseModel):
    id: int
    name: str
    active: bool

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    name: str
    cpf: str
    job_title: str
    employment_type: str
    base_salary: float
    department_id: int


class EmployeeOut(EmployeeCreate):
    id: int

    class Config:
        from_attributes = True


class VendorCreate(BaseModel):
    name: str
    document: str


class VendorOut(VendorCreate):
    id: int

    class Config:
        from_attributes = True


class BudgetAllocationCreate(BaseModel):
    code: str
    description: str
    amount: float
    fiscal_year_id: int


class BudgetAllocationOut(BudgetAllocationCreate):
    id: int

    class Config:
        from_attributes = True


class CommitmentCreate(BaseModel):
    number: str
    description: str
    amount: float
    fiscal_year_id: int
    department_id: int
    vendor_id: int


class CommitmentOut(CommitmentCreate):
    id: int
    status: str

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    commitment_id: int
    amount: float
    payment_date: date


class PaymentOut(PaymentCreate):
    id: int

    class Config:
        from_attributes = True


class ProcurementProcessCreate(BaseModel):
    number: str
    object_description: str
    status: str = "aberto"


class ContractCreate(BaseModel):
    number: str
    process_id: int
    vendor_id: int
    start_date: date
    end_date: date
    amount: float
    status: str = "vigente"


class AssetCreate(BaseModel):
    tag: str
    description: str
    classification: str
    location: str
    department_id: int
    responsible_employee_id: int | None = None
    value: float
    status: str = "ativo"


class PayrollCalculationRequest(BaseModel):
    month: str


class PayrollEventCreate(BaseModel):
    employee_id: int
    month: str
    kind: str
    description: str
    value: float


class AssetTransferRequest(BaseModel):
    to_department_id: int
    new_location: str | None = None
    new_responsible_employee_id: int | None = None


# ── Schemas de atualização parcial ────────────────────────────────────────────

class DepartmentUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: RoleEnum | None = None
    active: bool | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    document: str | None = None


class ProcurementProcessUpdate(BaseModel):
    object_description: str | None = None
    status: str | None = None


class ContractUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = None
    status: str | None = None


# ── Schemas de orçamento público: PPA / LDO / LOA ────────────────────────────

class PPAProgramCreate(BaseModel):
    code: str
    name: str
    objective: str = ""
    estimated_amount: float = 0.0


class PPAProgramOut(PPAProgramCreate):
    id: int
    ppa_id: int

    class Config:
        from_attributes = True


class PPACreate(BaseModel):
    period_start: int
    period_end: int
    description: str
    status: str = "rascunho"


class PPAOut(PPACreate):
    id: int
    created_at: datetime
    programs: list[PPAProgramOut] = []

    class Config:
        from_attributes = True


class PPAUpdate(BaseModel):
    description: str | None = None
    status: str | None = None


class LDOGoalCreate(BaseModel):
    code: str
    description: str
    category: str = "prioridade"


class LDOGoalOut(LDOGoalCreate):
    id: int
    ldo_id: int

    class Config:
        from_attributes = True


class LDOCreate(BaseModel):
    fiscal_year_id: int
    description: str
    status: str = "rascunho"


class LDOOut(LDOCreate):
    id: int
    created_at: datetime
    goals: list[LDOGoalOut] = []

    class Config:
        from_attributes = True


class LDOUpdate(BaseModel):
    description: str | None = None
    status: str | None = None


class LOAItemCreate(BaseModel):
    function_code: str
    subfunction_code: str
    program_code: str
    action_code: str
    description: str
    category: str = "despesa"
    authorized_amount: float
    executed_amount: float = 0.0


class LOAItemOut(LOAItemCreate):
    id: int
    loa_id: int

    class Config:
        from_attributes = True


class LOAItemUpdate(BaseModel):
    description: str | None = None
    authorized_amount: float | None = None
    executed_amount: float | None = None


class LOACreate(BaseModel):
    fiscal_year_id: int
    ldo_id: int | None = None
    description: str
    total_revenue: float = 0.0
    total_expenditure: float = 0.0
    status: str = "rascunho"


class LOAOut(LOACreate):
    id: int
    created_at: datetime
    items: list[LOAItemOut] = []

    class Config:
        from_attributes = True


class LOAUpdate(BaseModel):
    description: str | None = None
    total_revenue: float | None = None
    total_expenditure: float | None = None
    status: str | None = None


# ── Schemas de Protocolo ──────────────────────────────────────────────────────

class ProtocoloCreate(BaseModel):
    numero: str
    tipo: str
    assunto: str
    interessado: str
    interessado_doc: str | None = None
    origem_department_id: int | None = None
    destino_department_id: int | None = None
    status: str = "protocolado"
    prioridade: str = "normal"
    data_entrada: date
    prazo: date | None = None
    observacoes: str = ""


class ProtocoloUpdate(BaseModel):
    assunto: str | None = None
    destino_department_id: int | None = None
    status: str | None = None
    prioridade: str | None = None
    prazo: date | None = None
    observacoes: str | None = None


class TramitacaoCreate(BaseModel):
    para_department_id: int
    acao: str
    despacho: str = ""


class TramitacaoOut(BaseModel):
    id: int
    protocolo_id: int
    de_department_id: int | None
    para_department_id: int
    responsavel_id: int | None
    acao: str
    despacho: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProtocoloOut(BaseModel):
    id: int
    numero: str
    tipo: str
    assunto: str
    interessado: str
    interessado_doc: str | None
    origem_department_id: int | None
    destino_department_id: int | None
    status: str
    prioridade: str
    data_entrada: date
    prazo: date | None
    observacoes: str
    created_at: datetime
    tramitacoes: list[TramitacaoOut] = []

    model_config = ConfigDict(from_attributes=True)


# ── Schemas de Convênios ──────────────────────────────────────────────────────

class ConvenioCreate(BaseModel):
    numero: str
    objeto: str
    tipo: str = "recebimento"
    concedente: str
    cnpj_concedente: str | None = None
    valor_total: float
    contrapartida: float = 0.0
    data_assinatura: date
    data_inicio: date
    data_fim: date
    status: str = "vigente"
    department_id: int | None = None
    loa_item_id: int | None = None
    observacoes: str = ""


class ConvenioUpdate(BaseModel):
    objeto: str | None = None
    valor_total: float | None = None
    contrapartida: float | None = None
    data_fim: date | None = None
    status: str | None = None
    observacoes: str | None = None


class ConvenioDesembolsoCreate(BaseModel):
    numero_parcela: int
    valor: float
    data_prevista: date
    data_efetiva: date | None = None
    status: str = "previsto"
    observacoes: str = ""


class ConvenioDesembolsoOut(BaseModel):
    id: int
    convenio_id: int
    numero_parcela: int
    valor: float
    data_prevista: date
    data_efetiva: date | None
    status: str
    observacoes: str

    model_config = ConfigDict(from_attributes=True)


class ConvenioOut(BaseModel):
    id: int
    numero: str
    objeto: str
    tipo: str
    concedente: str
    cnpj_concedente: str | None
    valor_total: float
    contrapartida: float
    data_assinatura: date
    data_inicio: date
    data_fim: date
    status: str
    department_id: int | None
    loa_item_id: int | None
    observacoes: str
    created_at: datetime
    desembolsos: list[ConvenioDesembolsoOut] = []

    model_config = ConfigDict(from_attributes=True)


# ── Schemas de Tributário / Arrecadação ──────────────────────────────────────

class ContribuinteCreate(BaseModel):
    cpf_cnpj: str
    nome: str
    tipo: str = "PF"
    email: str | None = None
    telefone: str | None = None
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    municipio: str = ""
    uf: str = ""
    cep: str = ""


class ContribuinteUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    telefone: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cep: str | None = None
    ativo: bool | None = None


class ContribuinteOut(BaseModel):
    id: int
    cpf_cnpj: str
    nome: str
    tipo: str
    email: str | None
    telefone: str | None
    logradouro: str
    numero: str
    bairro: str
    municipio: str
    uf: str
    cep: str
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImovelCreate(BaseModel):
    inscricao: str
    contribuinte_id: int
    logradouro: str
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    area_terreno: float = 0.0
    area_construida: float = 0.0
    valor_venal: float = 0.0
    uso: str = "residencial"


class ImovelUpdate(BaseModel):
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    area_terreno: float | None = None
    area_construida: float | None = None
    valor_venal: float | None = None
    uso: str | None = None
    ativo: bool | None = None


class ImovelOut(BaseModel):
    id: int
    inscricao: str
    contribuinte_id: int
    logradouro: str
    numero: str
    complemento: str
    bairro: str
    area_terreno: float
    area_construida: float
    valor_venal: float
    uso: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class LancamentoCreate(BaseModel):
    contribuinte_id: int
    imovel_id: int | None = None
    tributo: str
    competencia: str           # YYYY-MM
    exercicio: int
    valor_principal: float
    valor_juros: float = 0.0
    valor_multa: float = 0.0
    valor_desconto: float = 0.0
    vencimento: date
    observacoes: str = ""


class LancamentoUpdate(BaseModel):
    valor_juros: float | None = None
    valor_multa: float | None = None
    valor_desconto: float | None = None
    vencimento: date | None = None
    status: str | None = None
    observacoes: str | None = None


class LancamentoOut(BaseModel):
    id: int
    contribuinte_id: int
    imovel_id: int | None
    tributo: str
    competencia: str
    exercicio: int
    valor_principal: float
    valor_juros: float
    valor_multa: float
    valor_desconto: float
    valor_total: float
    vencimento: date
    status: str
    data_pagamento: date | None
    observacoes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuiaOut(BaseModel):
    id: int
    lancamento_id: int
    codigo_barras: str
    valor: float
    vencimento: date
    status: str
    data_pagamento: date | None
    banco: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DividaAtivaCreate(BaseModel):
    lancamento_id: int
    numero_inscricao: str
    data_inscricao: date
    valor_atualizado: float
    observacoes: str = ""


class DividaAtivaUpdate(BaseModel):
    valor_atualizado: float | None = None
    status: str | None = None
    data_ajuizamento: date | None = None
    observacoes: str | None = None


class DividaAtivaOut(BaseModel):
    id: int
    lancamento_id: int
    contribuinte_id: int
    numero_inscricao: str
    tributo: str
    exercicio: int
    valor_original: float
    valor_atualizado: float
    data_inscricao: date
    status: str
    data_ajuizamento: date | None
    observacoes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Alíquotas IPTU ────────────────────────────────────────────────────────────

class AliquotaIPTUCreate(BaseModel):
    exercicio: int
    uso: str
    aliquota: float
    descricao: str = ""


class AliquotaIPTUUpdate(BaseModel):
    aliquota: float | None = None
    descricao: str | None = None


class AliquotaIPTUOut(BaseModel):
    id: int
    exercicio: int
    uso: str
    aliquota: float
    descricao: str

    model_config = ConfigDict(from_attributes=True)


# ── Parcelamento de dívida ativa ──────────────────────────────────────────────

class ParcelamentoDividaCreate(BaseModel):
    divida_id: int
    numero_parcelas: int
    valor_total: float
    data_acordo: date
    observacoes: str = ""


class ParcelamentoDividaUpdate(BaseModel):
    status: str | None = None
    observacoes: str | None = None


class ParcelaDividaOut(BaseModel):
    id: int
    parcelamento_id: int
    divida_id: int
    numero_parcela: int
    valor: float
    vencimento: date
    status: str
    data_pagamento: date | None

    model_config = ConfigDict(from_attributes=True)


class ParcelaDividaBaixa(BaseModel):
    data_pagamento: date


class ParcelamentoDividaOut(BaseModel):
    id: int
    divida_id: int
    numero_parcelas: int
    valor_total: float
    data_acordo: date
    status: str
    observacoes: str
    created_at: datetime
    parcelas: list["ParcelaDividaOut"] = []

    model_config = ConfigDict(from_attributes=True)


# ── Almoxarifado ──────────────────────────────────────────────────────────────

class ItemAlmoxarifadoCreate(BaseModel):
    codigo: str
    descricao: str
    unidade: str
    categoria: str = "geral"
    localizacao: str = ""
    estoque_minimo: float = 0.0
    valor_unitario: float = 0.0
    ativo: bool = True


class ItemAlmoxarifadoUpdate(BaseModel):
    descricao: str | None = None
    unidade: str | None = None
    categoria: str | None = None
    localizacao: str | None = None
    estoque_minimo: float | None = None
    valor_unitario: float | None = None
    ativo: bool | None = None


class ItemAlmoxarifadoOut(BaseModel):
    id: int
    codigo: str
    descricao: str
    unidade: str
    categoria: str
    localizacao: str
    estoque_minimo: float
    estoque_atual: float
    valor_unitario: float
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovimentacaoCreate(BaseModel):
    item_id: int
    tipo: str                           # entrada, saida
    quantidade: float
    valor_unitario: float = 0.0
    data_movimentacao: date
    departamento_id: int | None = None
    documento_ref: str = ""
    observacoes: str = ""


class MovimentacaoOut(BaseModel):
    id: int
    item_id: int
    tipo: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    data_movimentacao: date
    departamento_id: int | None
    responsavel_id: int | None
    documento_ref: str
    observacoes: str
    saldo_pos: float
    processo_id: int | None = None
    contrato_id: int | None = None
    recebimento_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Integração Compras ↔ Almoxarifado ─────────────────────────────────────────

class ItemRecebimentoCreate(BaseModel):
    item_almoxarifado_id: int
    quantidade_recebida: float
    valor_unitario: float = 0.0


class ItemRecebimentoOut(BaseModel):
    id: int
    recebimento_id: int
    item_almoxarifado_id: int
    quantidade_recebida: float
    valor_unitario: float
    valor_total: float
    movimentacao_id: int | None

    model_config = ConfigDict(from_attributes=True)


class RecebimentoCreate(BaseModel):
    processo_id: int
    contrato_id: int | None = None
    vendor_id: int | None = None
    commitment_id: int | None = None
    nota_fiscal: str = ""
    data_recebimento: date
    observacoes: str = ""
    itens: list[ItemRecebimentoCreate]


class RecebimentoOut(BaseModel):
    id: int
    processo_id: int
    contrato_id: int | None
    vendor_id: int | None
    commitment_id: int | None
    nota_fiscal: str
    data_recebimento: date
    status: str
    observacoes: str
    responsavel_id: int | None
    created_at: datetime
    itens: list[ItemRecebimentoOut] = []

    model_config = ConfigDict(from_attributes=True)
