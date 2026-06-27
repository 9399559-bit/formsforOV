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

const form = document.getElementById("leadForm");
const errorMessage = document.getElementById("errorMessage");
const successMessage = document.getElementById("successMessage");
const successTitle = document.getElementById("successTitle");
const submitButton = document.getElementById("submitButton");
const pdnConsent = document.getElementById("pdn_consent");

let toastTimer = null;

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

function showToast(message) {
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
    product_line: valueOf("product_line"),
    project: checkedValue("project"),
    start_date: valueOf("start_date"),
    financing_source: valueOf("financing_source"),
    preferred_communication: valueOf("preferred_communication"),
    comment: valueOf("comment"),
    pdn_consent: document.getElementById("pdn_consent").checked,
    m: managerLabel,
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
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

  submitButton.disabled = true;

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

    if (!response.ok || !result?.success) {
      throw new Error(result?.message || "Не удалось отправить заявку. Попробуйте ещё раз.");
    }

    form.reset();
    showToast("Спасибо, отправлено");
  } catch (error) {
    showError(error.message || "Не удалось отправить заявку. Попробуйте ещё раз.");
  } finally {
    // После reset чекбокс снова снят → кнопка станет disabled/бледной;
    // при ошибке согласие остаётся отмеченным → кнопка снова активна.
    updateSubmitState();
  }
});

pdnConsent.addEventListener("change", updateSubmitState);
updateSubmitState();
