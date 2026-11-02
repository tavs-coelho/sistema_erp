import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_default_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, demo_mode=False, secret_key="change-me-demo-secret",
                 database_url="sqlite:///safe.db")


def test_production_rejects_default_database_credentials():
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(_env_file=None, demo_mode=False, secret_key="a" * 48,
                 database_url="postgresql+psycopg2://erp:erp@db:5432/erp")


def test_production_accepts_explicit_secure_configuration():
    settings = Settings(_env_file=None, demo_mode=False, secret_key="a" * 48,
                        database_url="postgresql+psycopg2://erp:unique-password@db:5432/erp",
                        cors_allowed_origins="https://erp.example.org")
    assert settings.demo_mode is False
