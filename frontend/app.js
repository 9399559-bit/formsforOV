const form = document.getElementById("leadForm");
const errorMessage = document.getElementById("errorMessage");
const successMessage = document.getElementById("successMessage");
const successTitle = document.getElementById("successTitle");
const submitButton = document.getElementById("submitButton");

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("hidden");
}

function showSuccess(message) {
  successTitle.textContent = message;
  successMessage.classList.remove("hidden");
}

function clearMessages() {
  errorMessage.textContent = "";
  errorMessage.classList.add("hidden");
  successTitle.textContent = "Спасибо, заявка отправлена.";
  successMessage.classList.add("hidden");
}

function valueOf(id) {
  return document.getElementById(id).value.trim();
}

function collectPayload() {
  return {
    name: valueOf("name"),
    phone: valueOf("phone"),
    email: valueOf("email"),
    has_land: valueOf("has_land"),
    location: valueOf("location"),
    product_line: valueOf("product_line"),
    project: valueOf("project"),
    start_date: valueOf("start_date"),
    financing_source: valueOf("financing_source"),
    budget: valueOf("budget"),
    preferred_communication: valueOf("preferred_communication"),
    comment: valueOf("comment"),
    pdn_consent: document.getElementById("pdn_consent").checked,
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
    showSuccess("Спасибо, заявка отправлена.");
  } catch (error) {
    showError(error.message || "Не удалось отправить заявку. Попробуйте ещё раз.");
  } finally {
    submitButton.disabled = false;
  }
});
