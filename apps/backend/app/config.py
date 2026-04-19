from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema ERP Municipal"
    # Demo default only; override via environment variable in non-demo environments.
    secret_key: str = "change-me-demo-secret"
    algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_minutes: int = 60 * 24
    database_url: str = "postgresql+psycopg2://erp:erp@db:5432/erp"
    upload_dir: str = "/data/uploads"
    cors_allowed_origins: str = "http://localhost,http://127.0.0.1"
    demo_mode: bool = True
    # Rate limiting for /auth/login. Set LOGIN_RATE_LIMIT=10000/minute to disable in tests.
    login_rate_limit: str = "10/minute"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
