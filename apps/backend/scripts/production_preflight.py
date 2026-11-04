"""Fail-closed preflight for PUBLIC production deployment (not CI/demo).

Run: PYTHONPATH=apps/backend python -m scripts.production_preflight from apps/backend.
Exits nonzero if secrets, TLS/cookies, public origin or demonstration settings
could expose real municipal data. Never prints credential values.
"""
import os
from urllib.parse import urlsplit

from cryptography.fernet import Fernet

from app.config import Settings


def check() -> None:
    errors = []
    try:
        settings = Settings()
    except Exception as exc:
        raise SystemExit("ERRO: configuração de aplicação inválida") from exc
    if settings.demo_mode:
        errors.append("DEMO_MODE precisa estar desabilitado.")
    if not settings.browser_cookie_auth_enabled or not settings.browser_cookie_secure:
        errors.append("Sessão HttpOnly/Secure precisa estar habilitada.")
    origin = os.environ.get("ERP_PUBLIC_ORIGIN", "")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        errors.append("ERP_PUBLIC_ORIGIN precisa ser uma origem HTTPS válida, sem credenciais.")
    elif parsed.hostname in {"localhost", "127.0.0.1"}:
        errors.append("ERP_PUBLIC_ORIGIN não pode ser localhost.")
    allowed = settings.cors_origins
    if origin.rstrip("/") not in allowed:
        errors.append("CORS_ALLOWED_ORIGINS deve conter a origem HTTPS exata.")
    if any(o.startswith("http://") for o in allowed):
        errors.append("CORS não pode aceitar origens HTTP em produção.")
    if not settings.mfa_encryption_key:
        errors.append("MFA_ENCRYPTION_KEY não configurada.")
    else:
        try:
            Fernet(settings.mfa_encryption_key.encode("ascii"))
        except (ValueError, TypeError):
            errors.append("MFA_ENCRYPTION_KEY inválida.")
    if settings.database_url.startswith("sqlite"):
        errors.append("PostgreSQL obrigatório na implantação comercial.")
    if errors:
        raise SystemExit("ERRO de homologação:\n- " + "\n- ".join(errors))
    print("PASS: preflight estático de configurações de produção (não comprova HTTPS operacional)")


if __name__ == "__main__":
    check()
