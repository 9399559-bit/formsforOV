# MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working MVP skeleton on FastAPI and plain HTML/CSS/JavaScript for the Open Village 2026 lead form flow.

**Architecture:** FastAPI serves both the API and the static frontend to keep the first version simple and avoid cross-origin issues. The backend validates inbound lead payloads, builds the Bitrix24 payload, supports mock mode for local development, and can create real Bitrix24 leads when `BITRIX_ENABLED=true`.

**Tech Stack:** Python, FastAPI, Uvicorn, Pydantic, HTML, CSS, vanilla JavaScript.

---

## Current Status

- Backend FastAPI skeleton: completed.
- Public HTML/CSS/JavaScript form: completed.
- Mock Bitrix24 payload mode: completed.
- Real Bitrix24 test integration: completed.
- Verified minimal lead: `lead_id=29572`.
- Verified full questionnaire lead: `lead_id=29574`.
- Bitrix24 API errors during verified tests: none.
- `BITRIX_TEST_MODE` must remain enabled until the project owner explicitly approves disabling it.

## Next Stage

The next stage is UX/UI refinement of the public form and real-device verification on a phone.

Checklist for the next stage:
- Review form layout on mobile viewport.
- Check text readability and tap targets on a real phone.
- Verify submit flow on mobile network conditions.
- Keep `BITRIX_TEST_MODE=true` during all UX/UI checks that submit real leads.

---

### Task 1: Create backend application skeleton

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/requirements.txt`

- [ ] **Step 1: Add backend dependencies**

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic-settings==2.5.2
python-multipart==0.0.9
```

- [ ] **Step 2: Add app settings for mock mode and future Bitrix24 integration**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_port: int = 8000
    bitrix_webhook_url: str = ""
    bitrix_lead_source: str = "Open Village 2026"
    bitrix_source_channel: str = "web-form"
    bitrix_mock_mode: bool = True
    pdn_policy_url: str = "https://example.com/privacy-policy"
    pdn_consent_label: str = "Я даю согласие на обработку персональных данных"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Add FastAPI entrypoint with static frontend mounting**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Bot for OV2026 API")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
```

- [ ] **Step 4: Add package marker**

```python
"""Backend package for the Open Village 2026 MVP."""
```

### Task 2: Implement lead request validation and mock submission API

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/services.py`

- [ ] **Step 1: Add request/response schemas**

```python
from pydantic import BaseModel, EmailStr, Field, model_validator


class LeadCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    has_land: str | None = None
    location: str | None = None
    product_line: str | None = None
    project: str | None = None
    start_date: str | None = None
    financing_source: str | None = None
    budget: str | None = None
    preferred_communication: str | None = None
    comment: str | None = None
    pdn_consent: bool

    @model_validator(mode="after")
    def validate_contacts_and_consent(self) -> "LeadCreateRequest":
        phone = (self.phone or "").strip()
        email = str(self.email or "").strip()

        if not phone and not email:
            raise ValueError("Either phone or email is required.")

        if not self.pdn_consent:
            raise ValueError("Personal data consent is required.")

        self.name = self.name.strip()
        self.phone = phone or None
        self.comment = self.comment.strip() if self.comment else None
        return self


class LeadCreateResponse(BaseModel):
    success: bool
    message: str
```

- [ ] **Step 2: Add mock payload builder and logger**

```python
import json
import logging
from datetime import datetime, timezone

from .config import Settings
from .schemas import LeadCreateRequest


logger = logging.getLogger(__name__)


def build_bitrix_payload(data: LeadCreateRequest, settings: Settings) -> dict:
    payload = {
        "TITLE": f"{settings.bitrix_lead_source} - {data.name}",
        "NAME": data.name,
        "COMMENTS": data.comment or "",
        "SOURCE_DESCRIPTION": settings.bitrix_source_channel,
        "UF_CRM_PDN_CONSENT_TS": datetime.now(timezone.utc).isoformat(),
    }

    if data.phone:
        payload["PHONE"] = [{"VALUE": data.phone, "VALUE_TYPE": "WORK"}]

    if data.email:
        payload["EMAIL"] = [{"VALUE": str(data.email), "VALUE_TYPE": "WORK"}]

    optional_fields = {
        "HAS_LAND": data.has_land,
        "LOCATION": data.location,
        "PRODUCT_LINE": data.product_line,
        "PROJECT": data.project,
        "START_DATE": data.start_date,
        "FINANCING_SOURCE": data.financing_source,
        "BUDGET": data.budget,
        "PREFERRED_COMMUNICATION": data.preferred_communication,
    }
    payload.update({key: value for key, value in optional_fields.items() if value})
    return payload


def submit_lead(data: LeadCreateRequest, settings: Settings) -> dict:
    payload = build_bitrix_payload(data, settings)
    logger.info("Lead submission mock payload: %s", json.dumps(payload, ensure_ascii=False))
    return payload
```

- [ ] **Step 3: Add POST `/api/leads` endpoint**

```python
from fastapi import FastAPI

from .config import get_settings
from .schemas import LeadCreateRequest, LeadCreateResponse
from .services import submit_lead

settings = get_settings()
app = FastAPI(title="Bot for OV2026 API")


@app.post("/api/leads", response_model=LeadCreateResponse)
async def create_lead(payload: LeadCreateRequest) -> LeadCreateResponse:
    submit_lead(payload, settings)
    return LeadCreateResponse(
        success=True,
        message="Lead accepted in mock mode.",
    )
```

### Task 3: Build the public frontend form

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/styles.css`
- Create: `frontend/app.js`

- [ ] **Step 1: Add HTML form with required and optional fields**

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Open Village 2026 | iZBURG</title>
    <link rel="stylesheet" href="/static/styles.css" />
  </head>
  <body>
    <main class="page">
      <section class="card">
        <p class="eyebrow">Open Village 2026</p>
        <h1>Заявка на консультацию iZBURG</h1>
        <p class="intro">Оставьте контакт, и команда iZBURG свяжется с вами после выставки.</p>
        <div id="successMessage" class="success hidden">
          Спасибо, заявка отправлена. Мы свяжемся с вами в ближайшее время.
        </div>
        <div id="errorMessage" class="error hidden"></div>
        <form id="leadForm" novalidate>
          <label>
            Имя *
            <input id="name" name="name" type="text" maxlength="255" required />
          </label>
          <div class="grid">
            <label>
              Телефон
              <input id="phone" name="phone" type="tel" maxlength="50" />
            </label>
            <label>
              Email
              <input id="email" name="email" type="email" />
            </label>
          </div>
          <div class="grid">
            <label>
              Наличие участка
              <input id="has_land" name="has_land" type="text" />
            </label>
            <label>
              Локация
              <input id="location" name="location" type="text" />
            </label>
          </div>
          <div class="grid">
            <label>
              Линейка
              <input id="product_line" name="product_line" type="text" />
            </label>
            <label>
              Проект
              <input id="project" name="project" type="text" />
            </label>
          </div>
          <div class="grid">
            <label>
              Дата начала строительства
              <input id="start_date" name="start_date" type="text" />
            </label>
            <label>
              Источник финансирования
              <input id="financing_source" name="financing_source" type="text" />
            </label>
          </div>
          <div class="grid">
            <label>
              Бюджет
              <input id="budget" name="budget" type="text" />
            </label>
            <label>
              Удобный способ связи
              <input id="preferred_communication" name="preferred_communication" type="text" />
            </label>
          </div>
          <label>
            Комментарий
            <textarea id="comment" name="comment" rows="4"></textarea>
          </label>
          <label class="consent">
            <input id="pdn_consent" name="pdn_consent" type="checkbox" />
            <span>Я даю согласие на обработку персональных данных и принимаю <a href="#" target="_blank" rel="noreferrer">политику ПДн</a>.</span>
          </label>
          <p id="formHint" class="hint">* Обязательно: имя, хотя бы один контакт и согласие ПДн.</p>
          <button id="submitButton" type="submit">Отправить</button>
        </form>
      </section>
    </main>
    <script src="/static/app.js" defer></script>
  </body>
</html>
```

- [ ] **Step 2: Add CSS for form layout and states**

```css
body {
  margin: 0;
  font-family: "Arial", sans-serif;
  background: linear-gradient(135deg, #f3efe7 0%, #f9f7f2 100%);
  color: #1f2933;
}
```

- [ ] **Step 3: Add frontend validation and fetch submission**

```javascript
const form = document.getElementById("leadForm");
const errorMessage = document.getElementById("errorMessage");
const successMessage = document.getElementById("successMessage");
const submitButton = document.getElementById("submitButton");

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("hidden");
}

function clearMessages() {
  errorMessage.textContent = "";
  errorMessage.classList.add("hidden");
  successMessage.classList.add("hidden");
}

function collectPayload(formData) {
  return Object.fromEntries(formData.entries());
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessages();

  const formData = new FormData(form);
  const payload = collectPayload(formData);
  payload.pdn_consent = document.getElementById("pdn_consent").checked;

  if (!payload.name.trim()) {
    showError("Укажите имя.");
    return;
  }

  if (!payload.phone.trim() && !payload.email.trim()) {
    showError("Укажите телефон или email.");
    return;
  }

  if (!payload.pdn_consent) {
    showError("Нужно согласие на обработку персональных данных.");
    return;
  }

  submitButton.disabled = true;

  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok || !result.success) {
      throw new Error(result.message || "Не удалось отправить заявку.");
    }

    form.reset();
    successMessage.classList.remove("hidden");
  } catch (error) {
    showError(error.message);
  } finally {
    submitButton.disabled = false;
  }
});
```

### Task 4: Update environment template and README

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Add explicit FastAPI and Bitrix24 mock configuration**

```dotenv
APP_ENV=development
APP_PORT=8000
BITRIX_WEBHOOK_URL=https://your-bitrix-domain/rest/USER_ID/WEBHOOK_CODE/
BITRIX_LEAD_SOURCE=Open Village 2026
BITRIX_SOURCE_CHANNEL=web-form
BITRIX_MOCK_MODE=true
PDN_POLICY_URL=https://example.com/privacy-policy
PDN_CONSENT_LABEL=Я даю согласие на обработку персональных данных
LOG_LEVEL=INFO
```

- [ ] **Step 2: Document backend startup and frontend access**

```markdown
## Run locally

1. Create and activate a virtual environment.
2. Install dependencies from `backend/requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Start FastAPI with Uvicorn from the project root.
5. Open `http://127.0.0.1:8000/` in the browser.
```

### Task 5: Verify the MVP skeleton

**Files:**
- Verify only

- [ ] **Step 1: Install dependencies**

Run: `python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt`
Expected: dependencies install successfully

- [ ] **Step 2: Start the backend**

Run: `.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000`
Expected: server starts and serves the app

- [ ] **Step 3: Verify healthcheck**

Run: `curl -i http://127.0.0.1:8000/health`
Expected: `HTTP/1.1 200 OK` and `{"status":"ok"}`

- [ ] **Step 4: Verify frontend is served**

Run: `curl -i http://127.0.0.1:8000/`
Expected: `HTTP/1.1 200 OK` and HTML for the lead form

- [ ] **Step 5: Verify mock lead submission**

Run:

```bash
curl -i http://127.0.0.1:8000/api/leads \
  -H 'Content-Type: application/json' \
  -d '{"name":"Тест","phone":"+79990000000","email":"","pdn_consent":true}'
```

Expected: `HTTP/1.1 200 OK` and success JSON response
