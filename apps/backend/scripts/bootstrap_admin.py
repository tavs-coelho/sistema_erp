"""Create the FIRST administrator on a migrated, empty production database.

Use only from a trusted terminal with administrator-provided environment variables.
No HTTP route creates the initial administrator; this is a one-time offline action.
Never use the demonstration credentials for live entities.

Required:
  ERP_BOOTSTRAP_ADMIN_USERNAME
  ERP_BOOTSTRAP_ADMIN_EMAIL
  ERP_BOOTSTRAP_ADMIN_PASSWORD  (minimum 16 characters)
  ERP_BOOTSTRAP_ORGANIZATION
"""
import os
import sys

from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import RoleEnum, TenantBranding, User
from app.security import hash_password


def create_first_administrator(
    db: Session, *, username: str, email: str, password: str, organization: str,
) -> User:
    if db.query(User.id).first() is not None:
        raise ValueError("Bootstrap recusado: banco já possui usuários")
    username = username.strip()
    email = email.strip().lower()
    organization = organization.strip()
    if not (3 <= len(username) <= 80 and username.replace("_", "").replace("-", "").isalnum()):
        raise ValueError("Nome de usuário inválido")
    if not (6 <= len(email) <= 120 and "@" in email and "." in email.split("@")[-1]):
        raise ValueError("Endereço de e-mail inválido")
    if len(password) < 16 or len(password) > 128:
        raise ValueError("Senha inicial deve ter entre 16 e 128 caracteres")
    if not 3 <= len(organization) <= 120:
        raise ValueError("Nome da entidade inválido")
    if db.get(TenantBranding, 1) is None:
        db.add(TenantBranding(id=1, org_name=organization, app_title="ERP de Gestão Pública"))
    user = User(
        username=username, full_name=username, email=email,
        hashed_password=hash_password(password), role=RoleEnum.admin,
        tenant_id=1, active=True, must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    if settings.demo_mode:
        raise SystemExit("Defina DEMO_MODE=false para criar o administrador real")
    required = (
        "ERP_BOOTSTRAP_ADMIN_USERNAME", "ERP_BOOTSTRAP_ADMIN_EMAIL",
        "ERP_BOOTSTRAP_ADMIN_PASSWORD", "ERP_BOOTSTRAP_ORGANIZATION",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("Variáveis obrigatórias ausentes: " + ", ".join(missing))
    with SessionLocal() as db:
        user = create_first_administrator(
            db,
            username=os.environ[required[0]], email=os.environ[required[1]],
            password=os.environ[required[2]], organization=os.environ[required[3]],
        )
        print(f"Administrador inicial criado: id={user.id}, entidade=1")
    # Never echo passwords, token material or secrets.


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
