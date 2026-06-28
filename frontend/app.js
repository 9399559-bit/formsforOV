// Неугадываемая метка менеджера из URL формы (?m=...). Читаем один раз при
// загрузке. На фронт передаётся ТОЛЬКО метка — голый ID менеджера не приходит
// и нигде не отображается; резолв в ответственного делает бэкенд.
function readManagerLabel() {
  const raw = new URLSearchParams(window.location.search).get("m");
  if (!raw) return "";
  const trimmed = raw.trim();
  return /^[A-Za-z0-9_-]{1,64}$/.test(trimmed) ? trimmed : "";
}

const managerLabel = readManagerLabel();

// Слой 2 защиты от спама: cooldown на устройстве. Вспомогательный лимит поверх
// серверного IP-rate-limit — localStorage чистится/инкогнито обходит, поэтому он
// НЕ заменяет серверный слой, а работает параллельно.
const DEVICE_LIMIT_24H = 5;
const DEVICE_STORAGE_KEY = "ov2026_lead_submissions";
const DEVICE_WINDOW_MS = 24 * 60 * 60 * 1000;

// Читает timestamps отправок с этого устройства за последние 24 часа.
// При недоступном/битом localStorage возвращает [] — слой 2 просто молчит.
function readRecentDeviceSubmissions() {
  try {
    const raw = localStorage.getItem(DEVICE_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const cutoff = Date.now() - DEVICE_WINDOW_MS;
    return parsed.filter((ts) => typeof ts === "number" && ts > cutoff);
  } catch (error) {
    return [];
  }
}

function deviceLimitReached() {
  return readRecentDeviceSubmissions().length >= DEVICE_LIMIT_24H;
}

// Фиксирует успешную отправку с устройства (вызывать только после ответа 200).
function recordDeviceSubmission() {
  try {
    const recent = readRecentDeviceSubmissions();
    recent.push(Date.now());
    localStorage.setItem(DEVICE_STORAGE_KEY, JSON.stringify(recent));
  } catch (error) {
    // localStorage недоступен — серверный IP-лимит остаётся защитой.
  }
}

const form = document.getElementById("leadForm");
const errorMessage = document.getElementById("errorMessage");
const successMessage = document.getElementById("successMessage");
const successTitle = document.getElementById("successTitle");
const blockMessage = document.getElementById("blockMessage");
const submitButton = document.getElementById("submitButton");
const pdnConsent = document.getElementById("pdn_consent");

let toastTimer = null;
let isSubmitting = false;

// Кнопка активна только при отмеченном согласии ПДн. Реально выключаем submit
// (disabled), а не только подкрашиваем — чтобы заявка без согласия не уходила.
function updateSubmitState() {
  const consented = pdnConsent.checked;
  submitButton.disabled = !consented;
  submitButton.classList.toggle("submit-button--disabled", !consented);
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("hidden");
}

// Сообщение-ограничение у кнопки (device-лимит или серверный 429): запрос НЕ
// ушёл. Показываем рядом с submit и прячем toast «Спасибо» и верхнюю ошибку —
// блокировка не должна висеть одновременно с ними.
function showBlockMessage(message) {
  errorMessage.textContent = "";
  errorMessage.classList.add("hidden");
  successMessage.classList.add("hidden");
  blockMessage.textContent = message;
  blockMessage.classList.remove("hidden");
}

function showToast(message) {
  // «Спасибо» = запрос ушёл; снимаем блокировку, если была показана ранее.
  blockMessage.classList.add("hidden");
  successTitle.textContent = message;
  successMessage.classList.remove("hidden");
  if (toastTimer) {
    clearTimeout(toastTimer);
  }
  toastTimer = setTimeout(() => {
    successMessage.classList.add("hidden");
  }, 3500);
}

function clearMessages() {
  errorMessage.textContent = "";
  errorMessage.classList.add("hidden");
  successMessage.classList.add("hidden");
  blockMessage.textContent = "";
  blockMessage.classList.add("hidden");
}

function valueOf(id) {
  return document.getElementById(id).value.trim();
}

function checkedValue(name) {
  return new FormData(form).get(name)?.trim() || "";
}

function collectPayload() {
  return {
    name: valueOf("name"),
    phone: valueOf("phone"),
    email: valueOf("email"),
    has_land: checkedValue("has_land"),
    location: valueOf("location"),
    brand: checkedValue("brand"),
    start_date: valueOf("start_date"),
    financing_source: valueOf("financing_source"),
    preferred_communication: checkedValue("preferred_communication"),
    comment: valueOf("comment"),
    pdn_consent: document.getElementById("pdn_consent").checked,
    m: managerLabel,
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  // Защита от двойного клика: пока запрос в полёте, новый submit игнорируем
  // (кнопка уже disabled, флаг — страховка от повторного запроса).
  if (isSubmitting) {
    return;
  }

  clearMessages();

  const payload = collectPayload();

  if (!payload.name) {
    showError("Укажите имя.");
    return;
  }

  if (!payload.phone && !payload.email) {
    showError("Укажите телефон или email.");
    return;
  }

  if (!payload.pdn_consent) {
    showError("Нужно согласие на обработку персональных данных.");
    return;
  }

  // Слой 2: если с устройства за сутки уже ушло DEVICE_LIMIT_24H заявок —
  // запрос вообще не отправляем, показываем понятное сообщение.
  if (deviceLimitReached()) {
    showBlockMessage("Вы уже отправили несколько заявок. Если нужно ещё — обратитесь к менеджеру.");
    return;
  }

  // Состояние загрузки: мгновенно по клику, до ответа сервера.
  const originalLabel = submitButton.textContent;
  isSubmitting = true;
  submitButton.disabled = true;
  submitButton.classList.add("submit-button--loading");
  submitButton.textContent = "Отправляем...";

  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    let result = null;

    try {
      result = await response.json();
    } catch (parseError) {
      result = null;
    }

    // Серверный лимит (429): заявка отклонена. Показываем сообщение у кнопки,
    // а не общую ошибку вверху и не toast «Спасибо».
    if (response.status === 429) {
      showBlockMessage(result?.message || "Слишком много заявок. Попробуйте позже.");
      return;
    }

    if (!response.ok || !result?.success) {
      throw new Error(result?.message || "Не удалось отправить заявку. Попробуйте ещё раз.");
    }

    form.reset();
    // Только реальный успех (200) увеличивает счётчик устройства.
    recordDeviceSubmission();
    showToast("Спасибо, отправлено");
  } catch (error) {
    showError(error.message || "Не удалось отправить заявку. Попробуйте ещё раз.");
  } finally {
    // Снимаем состояние загрузки и возвращаем исходный текст кнопки.
    isSubmitting = false;
    submitButton.classList.remove("submit-button--loading");
    submitButton.textContent = originalLabel;
    // После reset чекбокс снова снят → кнопка станет disabled/бледной;
    // при ошибке согласие остаётся отмеченным → кнопка снова активна.
    updateSubmitState();
  }
});

pdnConsent.addEventListener("change", updateSubmitState);
updateSubmitState();

// Блокировка-крышка по таймеру не скрывается (в отличие от toast «Спасибо»):
// висит, пока человек снова не начнёт заполнять форму. Тогда убираем её, чтобы
// открыть кнопку для повторной отправки.
form.addEventListener("input", () => {
  if (!blockMessage.classList.contains("hidden")) {
    blockMessage.classList.add("hidden");
  }
});
