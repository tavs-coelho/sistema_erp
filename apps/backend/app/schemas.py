from datetime import date
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

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str


class DepartmentOut(DepartmentCreate):
    id: int

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
