import json
from pathlib import Path
from typing import Optional

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# managers.json лежит рядом с requirements.txt (в корне backend/), НЕ коммитится.
MANAGERS_CONFIG_PATH = Path(__file__).resolve().parents[1] / "managers.json"


class ManagersConfigError(RuntimeError):
    """Raised at startup when managers.json is missing or malformed."""


def load_managers_config(
    path: Path = MANAGERS_CONFIG_PATH,
) -> tuple[dict[str, int], int]:
    """Load and validate managers.json once at startup.

    Returns (mapping, fallback_responsible_id). Raises ManagersConfigError with a
    clear message if the file is missing or malformed, so startup fails loudly
    instead of breaking silently at request time.
    """
    if not path.exists():
        raise ManagersConfigError(
            f"managers.json not found at {path}. "
            "Create it next to requirements.txt (see project setup)."
        )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManagersConfigError(f"managers.json is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManagersConfigError("managers.json must be a JSON object.")

    managers = raw.get("managers")
    if not isinstance(managers, dict):
        raise ManagersConfigError(
            "managers.json must contain a 'managers' object mapping labels to ids."
        )

    mapping: dict[str, int] = {}
    for label, responsible_id in managers.items():
        if (
            not isinstance(label, str)
            or not isinstance(responsible_id, int)
            or isinstance(responsible_id, bool)
        ):
            raise ManagersConfigError(
                f"managers.json: invalid entry {label!r} -> {responsible_id!r}; "
                "expected a string label and an integer id."
            )
        mapping[label] = responsible_id

    fallback = raw.get("fallback_responsible_id")
    if not isinstance(fallback, int) or isinstance(fallback, bool):
        raise ManagersConfigError(
            "managers.json must contain an integer 'fallback_responsible_id'."
        )

    return mapping, fallback


class Settings(BaseSettings):
    app_env: str = "development"
    app_port: int = 8000
    frontend_base_url: str = "http://127.0.0.1:8000"
    bitrix_webhook_url: str = ""
    # Прежний дефолтный ответственный больше не управляет назначением лида —
    # его роль теперь играет fallback_responsible_id из managers.json.
    bitrix_default_assigned_by_id: Optional[int] = None
    bitrix_enabled: bool = False
    bitrix_test_mode: bool = True
    bitrix_lead_source: str = "Open Village 2026"
    bitrix_source_channel: str = "web"
    pdn_policy_url: str = "https://example.com/privacy-policy"
    pdn_consent_label: str = "Я даю согласие на обработку персональных данных"
    log_level: str = "INFO"
    database_url: str = ""

    # Слой 1 защиты от спама: пороги IP-rate-limit (принятых заявок на IP).
    rate_limit_10min: int = 5
    rate_limit_1h: int = 20

    # Заполняются из managers.json в get_settings(), а не из окружения.
    managers_mapping: dict[str, int] = {}
    fallback_responsible_id: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    mapping, fallback = load_managers_config()
    settings.managers_mapping = mapping
    settings.fallback_responsible_id = fallback
    return settings
