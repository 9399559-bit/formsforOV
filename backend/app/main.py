import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .bitrix import BitrixIntegrationError
from .config import get_settings
from .ratelimit import SlidingWindowRateLimiter, get_client_ip
from .schemas import LeadCreateRequest, LeadCreateResponse
from .services import submit_lead


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="Bot for OV2026 API")

# Слой 1: общий на процесс sliding-window лимитер по IP. In-memory, состояние
# живёт пока жив процесс — рестарт обнуляет счётчики (приемлемо).
rate_limiter = SlidingWindowRateLimiter(
    limit_10min=settings.rate_limit_10min,
    limit_1h=settings.rate_limit_1h,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Проверьте обязательные поля: имя, телефон или email, согласие на обработку персональных данных.",
        },
    )


@app.exception_handler(BitrixIntegrationError)
async def bitrix_exception_handler(request, exc: BitrixIntegrationError) -> JSONResponse:
    logging.getLogger(__name__).exception("Bitrix integration error")
    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            "message": "Не удалось отправить заявку. Попробуйте ещё раз позже.",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled application error")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Не удалось обработать заявку. Попробуйте ещё раз позже.",
        },
    )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/leads", response_model=LeadCreateResponse)
async def create_lead(payload: LeadCreateRequest, request: Request):
    # Слой 1: проверяем IP-лимит ДО любой обработки. При превышении в Битрикс
    # не идём. Логируем только факт + IP (не ПДн).
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip):
        logging.getLogger(__name__).warning(
            "rate limit exceeded ip=%s", client_ip
        )
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "message": "Слишком много заявок. Попробуйте позже.",
            },
        )

    result = submit_lead(payload, settings)
    # Считаем только реально принятые заявки — фиксируем после успешной отправки.
    rate_limiter.record(client_ip)
    return LeadCreateResponse(
        success=True,
        message="Заявка успешно принята.",
        lead_id=result.get("lead_id"),
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("__PDN_POLICY_URL__", settings.pdn_policy_url)
    html = html.replace("__PDN_CONSENT_LABEL__", settings.pdn_consent_label)
    return HTMLResponse(content=html)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
