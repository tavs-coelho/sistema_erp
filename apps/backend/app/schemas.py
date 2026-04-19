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
