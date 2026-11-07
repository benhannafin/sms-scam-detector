// Home and result views (decision 036). The message is kept in memory only and is
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
  const highlightNote = document.getElementById("highlight-note");
  const reasonsHeading = document.getElementById("reasons-heading");
  const reasonsList = document.getElementById("reasons");
  const navHow = document.getElementById("nav-how");
  const navBack = document.getElementById("nav-back");

  const MAX = Number(counter.dataset.max);
  const TOKENS = new Set(["urltoken", "moneytoken", "phonetoken"]);
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

  function confidenceBlock(label, confidence, template) {
    const block = document.createDocumentFragment();
    const line = document.createElement("p");
    line.className = "confidence-label";

    if (confidence === null) {
      line.textContent = template.dataset.notRecognised;
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

  function escapeRegExp(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Words and word pairs only: links, money and phone numbers aren't highlighted (decision 036).
  function findHighlights(message, reasons) {
    const ranges = [];
    for (const reason of reasons) {
      if (!reason.term) continue;
      const words = reason.term.split(" ");
      if (words.some((word) => TOKENS.has(word))) continue;
      const body = words.map(escapeRegExp).join("[^\\p{L}\\p{N}_]+");
      const pattern = new RegExp("(?<![\\p{L}\\p{N}_])" + body + "(?![\\p{L}\\p{N}_])", "giu");
      for (const match of message.matchAll(pattern)) {
        ranges.push([match.index, match.index + match[0].length]);
      }
    }
    ranges.sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const range of ranges) {
      const last = merged[merged.length - 1];
      if (last && range[0] < last[1]) {
        last[1] = Math.max(last[1], range[1]);
      } else {
        merged.push(range.slice());
      }
    }
    return merged;
  }

  function renderMessage(message, ranges) {
    messagePanel.replaceChildren();
    let position = 0;
    for (const [start, end] of ranges) {
      if (start > position) messagePanel.append(message.slice(position, start));
      const mark = document.createElement("mark");
      mark.textContent = message.slice(start, end);
      messagePanel.append(mark);
      position = end;
    }
    if (position < message.length) messagePanel.append(message.slice(position));
  }

  function showResult(message, result) {
    const template = document.getElementById("result-" + result.label) || document.getElementById("result-unsure");
    const label = template.id.replace("result-", "");
    const content = template.content.cloneNode(true);
    const hasSigns = result.reasons.some((reason) => reason.term !== null);
    const hamWithSigns = label === "ham" && hasSigns;

    if (hamWithSigns) content.querySelector(".summary").textContent = template.dataset.signsSummary;
    content.querySelector(".confidence").append(confidenceBlock(label, result.confidence, template));

    resultView.className = "view result--" + THEMES[label];
    verdictCard.replaceChildren(content);

    const ranges = findHighlights(message, result.reasons);
    renderMessage(message, ranges);
    highlightNote.hidden = ranges.length === 0;
    highlightNote.textContent = hamWithSigns ? template.dataset.signsNote : highlightNote.dataset.default;

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
