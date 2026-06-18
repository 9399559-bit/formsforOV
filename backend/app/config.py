from typing import Optional

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_port: int = 8000
    frontend_base_url: str = "http://127.0.0.1:8000"
    bitrix_webhook_url: str = ""
    bitrix_default_assigned_by_id: Optional[int] = None
    bitrix_enabled: bool = False
    bitrix_test_mode: bool = True
    bitrix_lead_source: str = "Open Village 2026"
    bitrix_source_channel: str = "web"
    pdn_policy_url: str = "https://example.com/privacy-policy"
    pdn_consent_label: str = "Я даю согласие на обработку персональных данных"
    log_level: str = "INFO"
    database_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
