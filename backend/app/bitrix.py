import json
import logging
from typing import Any, Union
from urllib import error, request

from .config import Settings


logger = logging.getLogger(__name__)


class BitrixIntegrationError(RuntimeError):
    """Raised when the real Bitrix24 integration cannot process the lead."""


def _safe_log_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only non-PII fields safe to log.

    Никогда не возвращает NAME / PHONE / EMAIL / COMMENTS / UF_CRM_* со
    значениями — только маршрутные метаданные заявки.
    """
    return {
        "channel": payload.get("channel"),
        "source": payload.get("source"),
        "assigned_by_id": payload.get("fields", {}).get("ASSIGNED_BY_ID"),
    }


def resolve_crm_lead_add_url(webhook_url: str) -> str:
    normalized = webhook_url.rstrip("/")
    if normalized.endswith("crm.lead.add") or normalized.endswith("crm.lead.add.json"):
        return normalized
    return f"{normalized}/crm.lead.add.json"


class MockBitrixClient:
    def create_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        logger.info("Lead submission (mock): %s", _safe_log_summary(payload))
        return {"mode": "mock", "lead_id": None, "payload": payload}


class RealBitrixClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.bitrix_webhook_url:
            raise BitrixIntegrationError("Bitrix webhook URL is missing.")

        # ASSIGNED_BY_ID всегда приходит в payload (метка m или fallback из
        # managers.json), поэтому отдельный default-ответственный может быть None.
        endpoint = resolve_crm_lead_add_url(self.settings.bitrix_webhook_url)
        body = json.dumps({"fields": payload["fields"]}, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=10) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            logger.exception("Bitrix HTTP error during lead creation")
            raise BitrixIntegrationError("Bitrix24 returned an HTTP error.") from exc
        except error.URLError as exc:
            logger.exception("Bitrix connection error during lead creation")
            raise BitrixIntegrationError("Bitrix24 is unreachable.") from exc

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as exc:
            logger.exception("Bitrix response is not valid JSON")
            raise BitrixIntegrationError("Bitrix24 returned an invalid response.") from exc

        if parsed.get("error"):
            # Не дампим parsed целиком: ответ может содержать эхо присланных
            # полей (ПДн). Логируем только код/описание ошибки.
            logger.error(
                "Bitrix API returned an application error: error=%s error_description=%s",
                parsed.get("error"),
                parsed.get("error_description"),
            )
            raise BitrixIntegrationError("Bitrix24 rejected the lead.")

        lead_id = parsed.get("result")
        if not isinstance(lead_id, int):
            # Тоже без дампа объекта — только ключи верхнего уровня.
            logger.error(
                "Bitrix API returned unexpected success payload; top-level keys: %s",
                list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__,
            )
            raise BitrixIntegrationError("Bitrix24 returned an unexpected response.")

        logger.info("Bitrix lead created successfully with id=%s", lead_id)
        return {"mode": "real", "lead_id": lead_id, "payload": payload, "raw_response": parsed}


def get_bitrix_client(settings: Settings) -> Union[MockBitrixClient, RealBitrixClient]:
    if settings.bitrix_enabled:
        return RealBitrixClient(settings)
    return MockBitrixClient()
