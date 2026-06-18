from datetime import datetime, timezone
from typing import Any

from .bitrix import get_bitrix_client
from .config import Settings
from .schemas import LeadCreateRequest


def build_bitrix_comments(
    data: LeadCreateRequest,
    channel: str,
    source: str,
    pdn_consent_timestamp: str,
    is_test_mode: bool,
) -> str:
    field_pairs = []

    if is_test_mode:
        field_pairs.append(("ВНИМАНИЕ", "ТЕСТОВАЯ ЗАЯВКА. НЕ ОБРАБАТЫВАТЬ."))

    field_pairs.extend([
        ("Имя", data.name),
        ("Телефон", data.phone or "не указано"),
        ("Email", str(data.email) if data.email else "не указано"),
        ("Локация", data.location or "не указано"),
        ("Предпочтительный способ связи", data.preferred_communication or "не указано"),
        ("Наличие участка", data.has_land or "не указано"),
        ("Линейка продукта", data.product_line or "не указано"),
        ("Дата начала строительства", data.start_date or "не указано"),
        ("Источник финансирования", data.financing_source or "не указано"),
        ("Проект", data.project or "не указано"),
        ("Бюджет", data.budget or "не указано"),
        ("Комментарий", data.comment or "не указано"),
        ("Channel", channel),
        ("Source", source),
        ("PDN consent timestamp", pdn_consent_timestamp),
    ])
    return "\n".join(f"{label}: {value}" for label, value in field_pairs)


def build_bitrix_payload(data: LeadCreateRequest, settings: Settings) -> dict[str, Any]:
    pdn_consent_timestamp = datetime.now(timezone.utc).isoformat()
    channel = settings.bitrix_source_channel
    source = settings.bitrix_lead_source
    title_prefix = "[TEST] " if settings.bitrix_test_mode else ""

    fields: dict[str, Any] = {
        "TITLE": f"{title_prefix}{settings.bitrix_lead_source} — {data.name} — веб",
        "NAME": data.name,
        "COMMENTS": build_bitrix_comments(
            data,
            channel,
            source,
            pdn_consent_timestamp,
            settings.bitrix_test_mode,
        ),
        "SOURCE_DESCRIPTION": "Open Village 2026 / web",
        "UF_CRM_1598531402": "80",
        "UF_CRM_CH_VYPODTVERZ": 1,
        "UF_CRM_T_NAZVANIEFOR": "Open Village 2026 — веб-форма",
        "UF_CRM_T_STRANICA": "Open Village 2026",
        "UF_CRM_1690179802": data.location or "",
        "UF_CRM_1690179814": data.preferred_communication or "",
        "UF_CRM_1690179826": data.has_land or "",
        "UF_CRM_1690179854": data.product_line or "",
        "UF_CRM_1690179882": data.start_date or "",
        "UF_CRM_1690179895": data.financing_source or "",
        "UF_CRM_1690179908": data.project or "",
        "UF_CRM_1690179923": data.budget or "",
        "UF_CRM_1690559724": data.phone or "",
        "UF_CRM_1690559734": str(data.email) if data.email else "",
    }

    if settings.bitrix_default_assigned_by_id is not None:
        fields["ASSIGNED_BY_ID"] = settings.bitrix_default_assigned_by_id

    if data.phone:
        fields["PHONE"] = [{"VALUE": data.phone, "VALUE_TYPE": "WORK"}]

    if data.email:
        fields["EMAIL"] = [{"VALUE": str(data.email), "VALUE_TYPE": "WORK"}]

    return {
        "channel": channel,
        "source": source,
        "fields": fields,
        "meta": {
            "channel": channel,
            "source": source,
            "pdn_consent": data.pdn_consent,
            "pdn_consent_timestamp": pdn_consent_timestamp,
            "bitrix_enabled": settings.bitrix_enabled,
            "bitrix_test_mode": settings.bitrix_test_mode,
        },
    }


def submit_lead(data: LeadCreateRequest, settings: Settings) -> dict:
    payload = build_bitrix_payload(data, settings)
    client = get_bitrix_client(settings)
    result = client.create_lead(payload)
    return {
        "payload": payload,
        "lead_id": result.get("lead_id"),
        "mode": result.get("mode"),
    }
