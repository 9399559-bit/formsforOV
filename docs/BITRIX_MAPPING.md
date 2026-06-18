# BITRIX_MAPPING

## 1. Цель интеграции

- Создавать лид в Bitrix24 через `crm.lead.add`.
- Не менять API frontend и не менять контракт `POST /api/leads`.
- Сохранить mock-режим для локальной разработки и безопасного тестирования.

## 2. Известные стандартные поля Bitrix24

- `TITLE`
- `NAME`
- `PHONE`
- `EMAIL`
- `COMMENTS`
- `ASSIGNED_BY_ID`

## 3. MVP mapping

### Стандартные поля

- `TITLE` = `"Open Village 2026 — {name} — веб"`
- `NAME` = `name`
- `PHONE` = `[{"VALUE": normalized_phone, "VALUE_TYPE": "WORK"}]`
- `EMAIL` = `[{"VALUE": normalized_email, "VALUE_TYPE": "WORK"}]`
- `COMMENTS` = все дополнительные данные формы, `channel`, `source`, `pdn_consent_timestamp`
- `ASSIGNED_BY_ID` = значение из `.env` `BITRIX_DEFAULT_ASSIGNED_BY_ID`
- `SOURCE_DESCRIPTION` = `"Open Village 2026 / web"`

### Пользовательские поля

- `UF_CRM_1598531402` = `"80"`  (`Источник трафика = Выставка`)
- `UF_CRM_CH_VYPODTVERZ` = `1`  (`согласие ПДн`)
- `UF_CRM_T_NAZVANIEFOR` = `"Open Village 2026 — веб-форма"`
- `UF_CRM_T_STRANICA` = `"Open Village 2026"`

### Поля анкеты

- `UF_CRM_1690179802` = `location`
- `UF_CRM_1690179814` = `preferred_communication`
- `UF_CRM_1690179826` = `has_land`
- `UF_CRM_1690179854` = `product_line`
- `UF_CRM_1690179882` = `start_date`
- `UF_CRM_1690179895` = `financing_source`
- `UF_CRM_1690179908` = `project`
- `UF_CRM_1690179923` = `budget`
- `UF_CRM_1690559724` = `normalized_phone`
- `UF_CRM_1690559734` = `normalized_email`

### Важные правила

- новые поля Bitrix не создавать;
- `SOURCE_ID` пока не использовать;
- источник выставки ставить через `UF_CRM_1598531402 = "80"`;
- дату согласия ПДн дополнительно писать в `COMMENTS`.

## 4. Поля, которые нужно подтвердить перед production

- финальный `BITRIX_DEFAULT_ASSIGNED_BY_ID` для production;
- список допустимых значений для перечислимых пользовательских полей;
- нужна ли дополнительная запись согласия ПДн помимо `UF_CRM_CH_VYPODTVERZ = 1` и `COMMENTS`;
- требуются ли дополнительные бизнес-правила для назначения ответственного.

## 5. Проверенные тесты

### Минимальный тестовый лид

- `lead_id=29572`
- Bitrix24 API ошибок не вернул.
- `TITLE` начинался с `[TEST]`.
- `PHONE` принят как multi-field.
- `EMAIL` принят как multi-field.
- `UF_CRM_1598531402=80` принят как источник трафика `Выставка`.
- `UF_CRM_CH_VYPODTVERZ=1` принят как согласие ПДн.
- `SOURCE_ID` не использовался.

### Полная анкета

- `lead_id=29574`
- Bitrix24 API ошибок не вернул.
- Все поля полной анкеты приняты Bitrix24 и сохранились в карточке лида.
- `UF_CRM_1598531402=80` соответствует источнику `Выставка`.
- `UF_CRM_CH_VYPODTVERZ=1` принято как согласие ПДн.
- `SOURCE_ID` не используется в MVP mapping.
- Дата и время согласия ПДн дополнительно записаны в `COMMENTS`.

## 6. Пример структуры полей

```json
{
  "fields": {
    "TITLE": "Open Village 2026 — Иван — веб",
    "NAME": "Иван",
    "PHONE": [
      {
        "VALUE": "+79990000000",
        "VALUE_TYPE": "WORK"
      }
    ],
    "EMAIL": [
      {
        "VALUE": "ivan@example.com",
        "VALUE_TYPE": "WORK"
      }
    ],
    "COMMENTS": "Локация: Москва\nChannel: web\nSource: Open Village 2026\nPDN consent timestamp: 2026-06-18T19:57:14.961886+00:00",
    "ASSIGNED_BY_ID": 42,
    "SOURCE_DESCRIPTION": "Open Village 2026 / web",
    "UF_CRM_1598531402": "80",
    "UF_CRM_CH_VYPODTVERZ": 1,
    "UF_CRM_T_NAZVANIEFOR": "Open Village 2026 — веб-форма",
    "UF_CRM_T_STRANICA": "Open Village 2026",
    "UF_CRM_1690179802": "Москва",
    "UF_CRM_1690179814": "Телефон",
    "UF_CRM_1690179826": "Да",
    "UF_CRM_1690179854": "iZBURG Line",
    "UF_CRM_1690179882": "2026",
    "UF_CRM_1690179895": "Ипотека",
    "UF_CRM_1690179908": "Проект 128",
    "UF_CRM_1690179923": "10-15 млн",
    "UF_CRM_1690559724": "+79990000000",
    "UF_CRM_1690559734": "ivan@example.com"
  }
}
```

## 7. Переменные `.env`

- `BITRIX_WEBHOOK_URL`
- `BITRIX_DEFAULT_ASSIGNED_BY_ID`
- `BITRIX_ENABLED=false`
- `BITRIX_TEST_MODE=true`

Дополнительно в MVP используются:
- `BITRIX_LEAD_SOURCE=Open Village 2026`
- `BITRIX_SOURCE_CHANNEL=web`

## 8. Правило переключения режимов

- Если `BITRIX_ENABLED=false`, backend работает в mock-режиме.
- Если `BITRIX_ENABLED=true`, backend отправляет лид в реальный Bitrix24.
- `BITRIX_TEST_MODE=true` оставляет тестовую пометку в `TITLE` и `COMMENTS`.
- Если при реальной отправке возникает ошибка Bitrix24, пользователь не должен видеть технические детали.

## 9. Архитектурное решение backend

### `backend/app/bitrix.py`

Содержит:
- mock-клиент для локальной разработки;
- реальный клиент Bitrix24;
- переключение mock/real через `BITRIX_ENABLED`.

### `backend/app/services.py`

Содержит orchestration-логику:
- принять валидированные данные;
- собрать payload по утверждённому MVP mapping;
- вызвать нужный Bitrix-клиент;
- вернуть результат в текущий flow без изменения API endpoint.

### `backend/app/main.py`

Содержит:
- `GET /health`;
- `POST /api/leads`;
- безопасную обработку ошибок валидации и интеграции.
