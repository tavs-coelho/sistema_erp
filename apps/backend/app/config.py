from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema ERP Municipal"
    secret_key: str = "change-me-demo-secret"
    algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_minutes: int = 60 * 24
    database_url: str = "postgresql+psycopg2://erp:erp@db:5432/erp"
    upload_dir: str = "/data/uploads"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
