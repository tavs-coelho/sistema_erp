from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
import re

from .models import RoleEnum

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$")


class BrandingOut(BaseModel):
    id: int
    subdomain: str | None = None
    org_name: str
    logo_url: str
    primary_color: str
    secondary_color: str
    accent_color: str
    favicon_url: str
    app_title: str
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BrandingUpdate(BaseModel):
    org_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    favicon_url: str | None = None
    app_title: str | None = None

    @field_validator("primary_color", "secondary_color", "accent_color", mode="before")
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _HEX_COLOR_RE.match(v):
            raise ValueError(f"Cor inválida: deve ser hexadecimal (#rrggbb). Recebido: {v!r}")
        normalized = v.lower()
        if len(normalized) == 4:
            normalized = "#" + "".join(ch * 2 for ch in normalized[1:])
        return normalized


class TenantCreate(BaseModel):
    subdomain: str
    org_name: str = "Prefeitura Municipal"
    primary_color: str = "#1d4ed8"
    secondary_color: str = "#0f172a"
    accent_color: str = "#0ea5e9"
    app_title: str = "Sistema ERP Municipal"

    @field_validator("subdomain")
    @classmethod
    def validate_subdomain(cls, v: str) -> str:
        import re as _re
        if not _re.match(r"^[a-z0-9]([a-z0-9\-]{0,62}[a-z0-9])?$", v):
            raise ValueError("Subdomínio inválido. Use apenas letras minúsculas, números e hífens.")
        return v.lower()


class TenantOut(BaseModel):
    id: int
    subdomain: str | None = None
    org_name: str
    app_title: str
    model_config = ConfigDict(from_attributes=True)



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
    loa_item_id: int | None = None


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


# ── Alerta de Estoque Mínimo + Requisição de Compra ───────────────────────────

class AlertaOut(BaseModel):
    id: int
    item_id: int
    movimentacao_id: int | None
    saldo_no_momento: float
    estoque_minimo: float
    status: str
    criado_em: datetime
    resolvido_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RequisicaoCompraCreate(BaseModel):
    item_id: int
    departamento_id: int | None = None
    alerta_id: int | None = None
    quantidade_sugerida: float
    justificativa: str = ""


class RequisicaoCompraVincular(BaseModel):
    processo_id: int


class RequisicaoCompraOut(BaseModel):
    id: int
    item_id: int
    departamento_id: int | None
    alerta_id: int | None
    processo_id: int | None
    quantidade_sugerida: float
    justificativa: str
    status: str
    solicitante_id: int | None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Frota ──────────────────────────────────────────────────────────────────────

class VeiculoCreate(BaseModel):
    placa: str
    descricao: str
    tipo: str = "leve"
    marca: str = ""
    modelo: str = ""
    ano_fabricacao: int | None = None
    combustivel: str = "flex"
    odometro_atual: float = 0.0
    departamento_id: int | None = None
    status: str = "ativo"
    observacoes: str = ""


class VeiculoUpdate(BaseModel):
    descricao: str | None = None
    tipo: str | None = None
    marca: str | None = None
    modelo: str | None = None
    ano_fabricacao: int | None = None
    combustivel: str | None = None
    odometro_atual: float | None = None
    departamento_id: int | None = None
    status: str | None = None
    observacoes: str | None = None


class VeiculoOut(BaseModel):
    id: int
    placa: str
    descricao: str
    tipo: str
    marca: str
    modelo: str
    ano_fabricacao: int | None
    combustivel: str
    odometro_atual: float
    departamento_id: int | None
    status: str
    observacoes: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class AbastecimentoCreate(BaseModel):
    veiculo_id: int
    data_abastecimento: date
    combustivel: str
    litros: float
    valor_litro: float = 0.0
    odometro: float = 0.0
    posto: str = ""
    nota_fiscal: str = ""
    departamento_id: int | None = None
    motorista_id: int | None = None
    movimentacao_id: int | None = None
    observacoes: str = ""


class AbastecimentoOut(BaseModel):
    id: int
    veiculo_id: int
    data_abastecimento: date
    combustivel: str
    litros: float
    valor_litro: float
    valor_total: float
    odometro: float
    posto: str
    nota_fiscal: str
    departamento_id: int | None
    motorista_id: int | None
    movimentacao_id: int | None
    observacoes: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemManutencaoCreate(BaseModel):
    descricao: str
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    item_almoxarifado_id: int | None = None


class ItemManutencaoOut(BaseModel):
    id: int
    manutencao_id: int
    descricao: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    item_almoxarifado_id: int | None
    movimentacao_id: int | None

    model_config = ConfigDict(from_attributes=True)


class ManutencaoCreate(BaseModel):
    veiculo_id: int
    tipo: str = "preventiva"
    descricao: str
    data_abertura: date
    odometro: float = 0.0
    oficina: str = ""
    departamento_id: int | None = None
    observacoes: str = ""
    itens: list[ItemManutencaoCreate] = []


class ManutencaoConcluir(BaseModel):
    data_conclusao: date
    valor_servico: float = 0.0
    oficina: str = ""
    observacoes: str = ""


class ManutencaoOut(BaseModel):
    id: int
    veiculo_id: int
    tipo: str
    descricao: str
    data_abertura: date
    data_conclusao: date | None
    odometro: float
    oficina: str
    valor_servico: float
    status: str
    departamento_id: int | None
    responsavel_id: int | None
    observacoes: str
    criado_em: datetime
    itens: list[ItemManutencaoOut] = []

    model_config = ConfigDict(from_attributes=True)


# ── NFS-e ─────────────────────────────────────────────────────────────────────

class NFSeCreate(BaseModel):
    prestador_id: int
    tomador_id: int | None = None
    descricao_servico: str
    codigo_servico: str = ""
    competencia: str           # YYYY-MM
    data_emissao: date
    valor_servico: float
    valor_deducoes: float = 0.0
    aliquota_iss: float        # percentual, ex: 2.5
    retencao_fonte: bool = False
    observacoes: str = ""


class NFSeUpdate(BaseModel):
    observacoes: str | None = None


class NFSeOut(BaseModel):
    id: int
    numero: str
    prestador_id: int
    tomador_id: int | None
    descricao_servico: str
    codigo_servico: str
    competencia: str
    data_emissao: date
    valor_servico: float
    valor_deducoes: float
    aliquota_iss: float
    valor_iss: float
    retencao_fonte: bool
    status: str
    nota_substituta_id: int | None
    lancamento_id: int | None
    observacoes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── ITBI ──────────────────────────────────────────────────────────────────────

class ITBICreate(BaseModel):
    transmitente_id: int
    adquirente_id: int
    imovel_id: int
    natureza_operacao: str = "compra_venda"
    data_operacao: date
    valor_declarado: float
    valor_venal_referencia: float = 0.0
    aliquota_itbi: float       # percentual, ex: 2.0
    observacoes: str = ""


class ITBIUpdate(BaseModel):
    valor_declarado: float | None = None
    valor_venal_referencia: float | None = None
    aliquota_itbi: float | None = None
    observacoes: str | None = None


class ITBIOut(BaseModel):
    id: int
    numero: str
    transmitente_id: int
    adquirente_id: int
    imovel_id: int
    natureza_operacao: str
    data_operacao: date
    valor_declarado: float
    valor_venal_referencia: float
    base_calculo: float
    aliquota_itbi: float
    valor_devido: float
    status: str
    lancamento_id: int | None
    observacoes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Ponto e Frequência ────────────────────────────────────────────────────────

class EscalaServidorCreate(BaseModel):
    employee_id: int
    horas_dia: float = 8.0
    dias_semana: str = "12345"
    hora_entrada: str = "08:00"
    hora_saida: str = "17:00"
    hora_inicio_intervalo: str = "12:00"
    hora_fim_intervalo: str = "13:00"


class EscalaServidorUpdate(BaseModel):
    horas_dia: float | None = None
    dias_semana: str | None = None
    hora_entrada: str | None = None
    hora_saida: str | None = None
    hora_inicio_intervalo: str | None = None
    hora_fim_intervalo: str | None = None


class EscalaServidorOut(BaseModel):
    id: int
    employee_id: int
    horas_dia: float
    dias_semana: str
    hora_entrada: str
    hora_saida: str
    hora_inicio_intervalo: str
    hora_fim_intervalo: str

    model_config = ConfigDict(from_attributes=True)


class RegistroPontoCreate(BaseModel):
    employee_id: int
    data: date
    tipo_registro: str        # entrada | saida | inicio_intervalo | fim_intervalo
    hora_registro: str        # HH:MM
    origem: str = "manual"
    observacoes: str = ""


class RegistroPontoOut(BaseModel):
    id: int
    employee_id: int
    data: date
    tipo_registro: str
    hora_registro: str
    origem: str
    observacoes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AbonoFaltaCreate(BaseModel):
    employee_id: int
    data: date
    tipo: str = "falta"       # falta | atraso | folga_compensacao
    motivo: str = ""


class AbonoFaltaUpdate(BaseModel):
    status: str               # pendente | aprovado | rejeitado
    motivo: str | None = None


class AbonoFaltaOut(BaseModel):
    id: int
    employee_id: int
    data: date
    tipo: str
    motivo: str
    status: str
    aprovado_por_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiaFrequenciaOut(BaseModel):
    """Resumo de um dia de trabalho para a folha de frequência."""
    data: date
    dia_semana: str             # "Seg", "Ter" …
    dia_util: bool
    entrada: str | None
    saida: str | None
    inicio_intervalo: str | None
    fim_intervalo: str | None
    horas_trabalhadas: float    # em horas decimais
    horas_extras: float
    minutos_atraso: int
    falta: bool
    abonado: bool
    abono_tipo: str | None
    status_dia: str             # presente | falta | falta_abonada | folga | fim_semana


class FolhaFrequenciaOut(BaseModel):
    employee_id: int
    employee_name: str
    periodo: str                # YYYY-MM
    total_dias_uteis: int
    total_presencas: int
    total_faltas: int
    total_faltas_abonadas: int
    total_horas_trabalhadas: float
    total_horas_extras: float
    total_minutos_atraso: int
    dias: list[DiaFrequenciaOut]


# ── Depreciação Patrimonial ───────────────────────────────────────────────────

class ConfiguracaoDepreciacaoCreate(BaseModel):
    asset_id: int
    data_aquisicao: date
    valor_aquisicao: float
    vida_util_meses: int
    valor_residual: float = 0.0
    metodo: str = "linear"      # linear | saldo_decrescente


class ConfiguracaoDepreciacaoUpdate(BaseModel):
    data_aquisicao: date | None = None
    valor_aquisicao: float | None = None
    vida_util_meses: int | None = None
    valor_residual: float | None = None
    metodo: str | None = None
    ativo: bool | None = None


class ConfiguracaoDepreciacaoOut(BaseModel):
    id: int
    asset_id: int
    data_aquisicao: date
    valor_aquisicao: float
    vida_util_meses: int
    valor_residual: float
    metodo: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class LancamentoDepreciacaoOut(BaseModel):
    id: int
    asset_id: int
    periodo: str
    valor_depreciado: float
    depreciacao_acumulada: float
    valor_contabil_liquido: float
    criado_por_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalcularDepreciacaoRequest(BaseModel):
    periodo: str                          # YYYY-MM
    asset_id: int | None = None           # None = todos os bens configurados


class ItemRelatorioDepreciacaoOut(BaseModel):
    periodo: str
    valor_depreciado: float
    depreciacao_acumulada: float
    valor_contabil_liquido: float


class RelatorioDepreciacaoOut(BaseModel):
    asset_id: int
    asset_tag: str
    asset_description: str
    valor_aquisicao: float
    valor_residual: float
    vida_util_meses: int
    metodo: str
    data_aquisicao: date
    lancamentos: list[ItemRelatorioDepreciacaoOut]


# ── Integração Ponto → Folha ──────────────────────────────────────────────────

class ConfiguracaoIntegracaoPontoCreate(BaseModel):
    employee_id: int
    desconto_falta_diaria: float | None = None   # None = proporcional ao salário
    percentual_hora_extra: float = 50.0
    desconto_atraso: bool = True


class ConfiguracaoIntegracaoPontoUpdate(BaseModel):
    desconto_falta_diaria: float | None = None
    percentual_hora_extra: float | None = None
    desconto_atraso: bool | None = None
    ativo: bool | None = None


class ConfiguracaoIntegracaoPontoOut(BaseModel):
    id: int
    employee_id: int
    desconto_falta_diaria: float | None
    percentual_hora_extra: float
    desconto_atraso: bool
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class IntegrarPontoFolhaRequest(BaseModel):
    periodo: str                   # YYYY-MM
    employee_id: int | None = None # None = todos com configuração ativa
    force: bool = False            # re-processa mesmo se já integrado
    recalcular_payslip: bool = False   # recalcula holerite automaticamente após integração
    taxa_deducao: float = 11.0     # taxa de dedução (%) usada se recalcular_payslip=True


class IntegracaoLogOut(BaseModel):
    id: int
    employee_id: int
    periodo: str
    faltas_descontadas: int
    horas_extras_creditadas: float
    valor_desconto_faltas: float
    valor_desconto_atrasos: float
    valor_credito_horas_extras: float
    status: str
    executado_por_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Recálculo Payslip ─────────────────────────────────────────────────────────

class RecalcularPayslipRequest(BaseModel):
    periodo: str                    # YYYY-MM
    employee_id: int | None = None  # None = todos os servidores do período
    taxa_deducao: float = 11.0      # % de dedução sobre gross (padrão INSS simplificado)


class RecalcularPayslipItemOut(BaseModel):
    employee_id: int
    employee_name: str
    periodo: str
    gross_amount: float
    deductions: float
    net_amount: float
    status: str   # criado | atualizado | erro
    variacao_net: float   # net_novo - net_anterior (0 se criado)

    model_config = ConfigDict(from_attributes=True)


class RecalcularPayslipOut(BaseModel):
    periodo: str
    total_criados: int
    total_atualizados: int
    total_erros: int
    resultados: list[RecalcularPayslipItemOut]


# ── SICONFI / SIOP ────────────────────────────────────────────────────────────

class ConfiguracaoEntidadeCreate(BaseModel):
    nome_entidade: str
    cnpj: str
    codigo_ibge: str
    uf: str
    esfera: str = "Municipal"
    poder: str = "Executivo"
    tipo_entidade: str = "Prefeitura Municipal"
    responsavel_nome: str = ""
    responsavel_cargo: str = ""
    responsavel_cpf: str = ""


class ConfiguracaoEntidadeOut(ConfiguracaoEntidadeCreate):
    id: int
    ativo: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportacaoRequest(BaseModel):
    tipo: str                     # finbra | rreo | rgf | siop_programas
    exercicio: int
    periodo: str | None = None    # ex: "bimestre_3" | "quad_2"


class ExportacaoOut(BaseModel):
    id: int
    tipo: str
    exercicio: int
    periodo: str | None
    status: str
    inconsistencias: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InconsistenciaItem(BaseModel):
    severidade: str    # ERRO | AVISO
    codigo: str
    mensagem: str
    valor_encontrado: str | None = None
    valor_esperado: str | None = None


# ── SICONFI Onda 19 — XML + Envio ─────────────────────────────────────────────

class ValidacaoXmlRequest(BaseModel):
    tipo: str               # finbra | rreo | rgf
    exercicio: int
    periodo: str | None = None  # bimestre_N | quad_N


class ValidacaoXmlOut(BaseModel):
    id: int
    tipo: str
    exercicio: int
    periodo: str | None
    valido: bool
    erros_xsd: list[str] | None
    avisos: list[str] | None
    xsd_fonte: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnvioSiconfiRequest(BaseModel):
    """Stub de configuração para envio real (Fase 2)."""
    validacao_xml_id: int
    certificado_pfx_base64: str  # certificado A1 PFX codificado em base64
    certificado_senha: str        # senha do PFX
    url_webservice: str = "https://siconfi.tesouro.gov.br/siconfi/api/public/relatorios"
    dry_run: bool = True          # se True, simula envio sem postar


class EnvioSiconfiOut(BaseModel):
    id: int
    tipo: str
    exercicio: int
    periodo: str | None
    status: str
    protocolo: str | None
    http_status: int | None
    certificado_serial: str | None
    tentativas: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Escala de Férias ──────────────────────────────────────────────────────────

class EscalaFeriasCreate(BaseModel):
    employee_id: int
    ano_referencia: int
    data_inicio: date
    data_fim: date
    fracao: int = 1
    observacoes: str = ""


class EscalaFeriasUpdate(BaseModel):
    data_inicio: date | None = None
    data_fim: date | None = None
    status: str | None = None
    observacoes: str | None = None


class EscalaFeriasOut(BaseModel):
    id: int
    employee_id: int
    ano_referencia: int
    data_inicio: date
    data_fim: date
    dias_gozados: int
    fracao: int
    status: str
    aprovado_por_id: int | None
    observacoes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
