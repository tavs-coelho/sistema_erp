from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


INSECURE_KEYS = {"change-me-demo-secret", "changeme", "secret", "demo-secret"}


class Settings(BaseSettings):
    app_name: str = "Sistema ERP Municipal"
    secret_key: str = "change-me-demo-secret"
    algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_minutes: int = 60 * 24
    database_url: str = "postgresql+psycopg2://erp:erp@db:5432/erp"
    upload_dir: str = "/data/uploads"
    cors_allowed_origins: str = "http://localhost,http://127.0.0.1"
    demo_mode: bool = True
    login_rate_limit: str = "10/minute"
    mfa_encryption_key: str | None = None

    # Opt-in browser cookie mode. Existing bearer-token API remains unchanged.
    browser_cookie_auth_enabled: bool = False
    browser_cookie_secure: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @model_validator(mode="after")
    def validate_production_configuration(self):
        if not self.demo_mode:
            if len(self.secret_key) < 32 or self.secret_key.lower() in INSECURE_KEYS:
                raise ValueError("SECRET_KEY must be a strong, unique value (at least 32 characters) outside demo mode")
            if self.database_url.startswith("postgresql") and "://erp:erp@" in self.database_url:
                raise ValueError("Default PostgreSQL credentials are forbidden outside demo mode")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are forbidden outside demo mode")
            if self.browser_cookie_auth_enabled and not self.browser_cookie_secure:
                raise ValueError("Secure cookies are required for browser authentication in production")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
