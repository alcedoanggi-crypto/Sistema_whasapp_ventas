from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://wa_app:wa_pass@localhost:5432/whatsapp_ventas"
    redis_url: str = "redis://localhost:6379/3"

    secret_key: str = "dev-secret"
    admin_email: str = "admin@demo.com"
    admin_password: str = "admin123"
    integration_api_key: str = "clave-integracion-demo"

    whatsapp_mode: str = "sandbox"  # sandbox | cloud
    whatsapp_api_version: str = "v21.0"
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_app_secret: str = "app-secret-demo"
    whatsapp_verify_token: str = "verify-token-demo"

    rate_limit_mps: int = 20
    max_reintentos: int = 5
    ventana_atribucion_dias: int = 7
    celery_eager: bool = False

    frontend_origin: str = "http://localhost:5174"

    @property
    def sandbox(self) -> bool:
        return self.whatsapp_mode.lower() != "cloud"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
