// Home and result views (decisions 036, 042). The message is kept in memory only and is
// only ever inserted as text, never as HTML.
(function () {
  "use strict";

  const form = document.getElementById("check-form");
  const textarea = document.getElementById("message");
  const counter = document.getElementById("counter");
  const checkButton = document.getElementById("check-button");
  const checking = document.getElementById("checking");
  const errorBox = document.getElementById("message-error");
  const errorText = document.getElementById("message-error-text");
  const homeView = document.getElementById("home-view");
  const resultView = document.getElementById("result-view");
  const verdictCard = document.getElementById("verdict-card");
  const messagePanel = document.getElementById("result-message");
  const reasonsHeading = document.getElementById("reasons-heading");
  const reasonsList = document.getElementById("reasons");
  const navHow = document.getElementById("nav-how");
  const navBack = document.getElementById("nav-back");

  const MAX = Number(counter.dataset.max);
  const THEMES = { smishing: "scam", spam: "spam", ham: "legit", unsure: "unsure" };

  // Counts characters the way the API does, so an emoji counts as one.
  function characterCount(text) {
    return Array.from(text).length;
  }

  function updateCounter() {
    counter.textContent = characterCount(textarea.value) + " / " + MAX + " characters";
  }

  // ---------- Problem with input ----------

  function showError(code) {
    const source =
      document.querySelector('#error-messages [data-code="' + code + '"]') ||
      document.querySelector('#error-messages [data-code="generic"]');
    errorText.replaceChildren(...Array.from(source.childNodes, (node) => node.cloneNode(true)));
    errorBox.hidden = false;
    textarea.setAttribute("aria-invalid", "true");
    textarea.focus();
  }

  function clearError() {
    errorBox.hidden = true;
    errorText.replaceChildren();
    textarea.removeAttribute("aria-invalid");
  }

  function setChecking(isChecking) {
    checkButton.hidden = isChecking;
    checking.hidden = !isChecking;
    textarea.setAttribute("aria-busy", String(isChecking));
  }

  // ---------- Showing a view ----------

  function showView(view, other) {
    other.hidden = true;
    other.classList.remove("is-entering");
    view.hidden = false;
    view.classList.remove("is-entering");
    void view.offsetWidth; // restart the animation
    view.classList.add("is-entering");
    window.scrollTo(0, 0);
  }

  // ---------- Result ----------

  // Rounded down, so an Unsure result never shows 70%, and capped so nothing claims 100%.
  function percent(confidence) {
    return Math.min(99, Math.floor(confidence * 100 + 1e-9));
  }

  function confidenceBlock(label, confidence, status, template) {
    const block = document.createDocumentFragment();
    const line = document.createElement("p");
    line.className = "confidence-label";

    // No meter when there's no confidence to show (decisions 032, 041).
    if (confidence === null) {
      line.textContent = status === "warning_signs" ? template.dataset.warningSigns : template.dataset.notRecognised;
      block.append(line);
      return block;
    }

    const value = percent(confidence);
    const strong = document.createElement("strong");
    if (label === "unsure") {
      strong.textContent = value + "%, too low to rate";
      line.append(strong);
    } else {
      const name = document.createElement("span");
      name.textContent = "Confidence";
      strong.textContent = value + "%";
      line.append(name, strong);
    }

    const meter = document.createElement("div");
    meter.className = "meter";
    meter.setAttribute("role", "img");
    meter.setAttribute("aria-label", label === "unsure" ? value + "%, too low to rate" : "Confidence " + value + "%");
    const fill = document.createElement("div");
    fill.className = "meter-fill";
    fill.style.width = value + "%";
    meter.append(fill);

    block.append(line, meter);
    return block;
  }

  function showResult(message, result) {
    const template = document.getElementById("result-" + result.label) || document.getElementById("result-unsure");
    const label = template.id.replace("result-", "");
    const content = template.content.cloneNode(true);
    const hasSigns = result.reasons.some((reason) => reason.term !== null);
    const hamWithSigns = label === "ham" && hasSigns;

    if (hamWithSigns) content.querySelector(".summary").textContent = template.dataset.signsSummary;
    content.querySelector(".confidence").append(confidenceBlock(label, result.confidence, result.status, template));

    resultView.className = "view result--" + THEMES[label];
    verdictCard.replaceChildren(content);

    // Plain text, no highlights: highlighted words would suggest they're why a message is a scam,
    // which isn't how the model works (decision 042).
    messagePanel.textContent = message;

    reasonsHeading.textContent = hamWithSigns ? template.dataset.signsHeading : reasonsHeading.dataset.default;
    reasonsList.replaceChildren();
    const texts = result.reasons.length
      ? result.reasons.map((reason) => reason.text)
      : [document.getElementById("result-unsure").dataset.noReasons];
    for (const text of texts) {
      const item = document.createElement("li");
      const dot = document.createElement("span");
      dot.className = "dot";
      dot.setAttribute("aria-hidden", "true");
      const words = document.createElement("span");
      words.textContent = text;
      item.append(dot, words);
      reasonsList.append(item);
    }

    navHow.hidden = true;
    navBack.hidden = false;
    showView(resultView, homeView);
    verdictCard.querySelector(".verdict").focus();
  }

  function checkAnother() {
    textarea.value = "";
    updateCounter();
    clearError();
    navBack.hidden = true;
    navHow.hidden = false;
    showView(homeView, resultView);
    textarea.focus();
  }

  // ---------- Talking to POST /api/check ----------

  async function check(message) {
    clearError();
    setChecking(true);
    try {
      const response = await fetch(form.dataset.apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message }),
      });
      let body = null;
      try {
        body = await response.json();
      } catch (error) {
        body = null;
      }
      setChecking(false);
      if (response.ok && body) {
        showResult(message, body);
      } else {
        showError(body && body.error ? body.error.code : "generic");
      }
    } catch (error) {
      setChecking(false);
      showError("generic");
    }
  }

  // ---------- Wiring ----------

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    check(textarea.value);
  });

  textarea.addEventListener("input", () => {
    updateCounter();
    if (!errorBox.hidden) clearError();
  });

  for (const chip of document.querySelectorAll(".chip")) {
    chip.addEventListener("click", () => {
      textarea.value = chip.dataset.message;
      updateCounter();
      clearError();
      textarea.focus();
    });
  }

  for (const button of document.querySelectorAll(".js-check-another")) {
    button.addEventListener("click", checkAnother);
  }

  updateCounter();
})();
