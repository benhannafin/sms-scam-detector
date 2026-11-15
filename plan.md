# SMS Scam Detector – Build Plan

**Rule:** before starting a stage, update this file: fill in the stage's goal, scope, files, interfaces, tests and definition of done, and set it to *In progress*. When it's finished, tick the checklist, add notes and set it to *Done*. Any change to the design goes in `docs/decisions.md` at the same time.

## What we're building

A web app where someone pastes a text message and gets back **Legitimate**, **Marketing spam** or **Likely scam**, with a confidence level and the reasons. Low-confidence results show **Unsure**. The app never says a message is "safe" and never stores messages.

## Architecture

Layered modular monolith: one Flask app, one module per component, modules talk only through their interfaces.

| Layer | Module | Interface (in → out) |
| --- | --- | --- |
| Presentation | `web` | Pages: check, result, problem with input |
| API | `api` | `POST /api/check`: `{message}` → `{label, confidence, status, reasons}` |
| Application | `check_service` | Check a message: text → check result (applies the Unsure rule) |
| ML | `preprocessor` | Clean the text: raw text → cleaned text with tokens |
| ML | `classifier` | Classify: cleaned text → label + probability per class + recognised-term count + term contributions; Load model: version → model |
| ML | `explainer` | Explain: cleaned text + prediction → up to 3 reasons, each a warning sign with why it matters, or a fallback (decision 043) |
| Application | `signals` | Find signs: cleaned text → list of warning signs; 3 of the 11 can change a result (decisions 041, 043) |
| Offline | `training` | Trains, evaluates and saves the model file |

Not built yet (designed for later): feedback API, feedback service and store, scheduled retraining, monitoring.

## Conventions

- Python 3, Flask, scikit-learn, pandas, joblib, pytest, Flask-Limiter
- One folder per module under `app/`; one test file per module under `tests/`
- Modules never reach into each other's internals – only through the interface
- Every change comes with tests; `pytest` runs everything with one command
- Message text is never written to disk or logs
- No secrets in the code

## Workflow for every stage

1. **Plan** – update this file; have Claude Code plan the stage; review and approve before code is written.
2. **Build** – one module only.
3. **Test** – tests for that module; all tests pass before moving on.
4. **Understand** – get a plain-English explanation; write your own short summary in `docs/learning_log.md`.
5. **Commit and push** – small commits, clear messages.
6. **Record decisions** – any design change goes in `docs/decisions.md`.
7. **Hand over** – at the end of every session, update `handover.md`.

## Stages

| # | Stage | Status |
| --- | --- | --- |
| 0 | Project setup | Done |
| 1 | Data loading and cleaning | Done |
| 2 | Text preprocessor | Done |
| 3 | Training pipeline | Done |
| 4 | Classifier (+ mock) | Done |
| 5 | Explainer | Done |
| 6 | Check service | Done |
| 7 | REST API | Done |
| 8 | Web UI | Done |
| 9 | Deployment (Azure App Service) | Done |
| 10 | Self-review and fixes | Done |
| 11 | Tuning and evaluation | Done |
| 12 | Failure handling and hardening | In progress |
| 13 | User testing and final fixes | Not started |

---

## Stage template

```
## Stage N – Name
**Status:** Not started / In progress / Done
**Goal:**
**In scope:**
**Out of scope:**
**Files:**
**Interfaces (in → out):**
**Tests:**
**Done when:**
- [ ] ...
**Open questions:**
**Notes after finishing:**
```

---

## Stage 0 – Project setup

**Status:** Done
**Goal:** a correctly structured, empty project whose test suite runs with one command.

**In scope:** repo; folder structure matching the architecture; virtual environment and `requirements.txt`; `CLAUDE.md`; `.gitignore`; `README.md` skeleton; `docs/decisions.md` and `docs/learning_log.md`; dataset in `data/` with credit (CC BY 4.0).
**Out of scope:** application code.

```
sms-scam-detector/
├── app/
│   ├── web/
│   ├── api/
│   ├── check_service/
│   ├── preprocessor/
│   ├── classifier/
│   └── explainer/
├── training/
├── models/
├── data/
├── tests/
├── docs/
├── CLAUDE.md
├── plan.md
├── requirements.txt
└── README.md
```

**Done when:**
- [ ] Repo created and pushed
- [ ] Structure matches the architecture
- [ ] `pip install -r requirements.txt` works in a fresh environment
- [ ] `pytest` runs and passes (placeholder test)
- [ ] `CLAUDE.md` written and reviewed
- [ ] Dataset in `data/` with attribution

**Decided:** repo name `sms-scam-detector`; dataset committed to the repo with attribution in `data/README.md`.

---

## Stage 1 – Data loading and cleaning
**Status:** Done
**Goal:** load the CSV and return a clean dataset for training.
**In scope:** read the CSV as UTF-8; keep only `LABEL` and `TEXT`; trim whitespace; normalise label spelling; remove every message with conflicting labels; remove duplicates. Cleaning runs in code on every load; the CSV is never changed and no cleaned copy is saved. See decision 029.
**Out of scope:** lowercasing and token replacement (Stage 2); train/test split (Stage 3); repairing the `�` characters already in the file.
**Files:** `training/data.py`, `tests/test_data.py`.
**Interfaces (in → out):** Load the dataset: `load_dataset(path=<the dataset CSV>)` → pandas DataFrame with columns `label` (`ham`, `spam` or `smishing`) and `text`. Used only by `training/`; the web app never loads the dataset.
**Tests:**
- Small temporary CSVs check each rule on its own: UTF-8 `£` is read correctly; only `label` and `text` are returned; whitespace is trimmed; label spelling is normalised; duplicates that differ only by a leading tab become one row; conflicting messages are removed completely, including when one copy has a leading tab.
- An unrecognised label raises a clear error.
- The real dataset gives 5,797 rows: 4,834 ham, 528 smishing, 435 spam.
**Done when:**
- [x] `load_dataset` returns the cleaned dataset with the expected counts
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** the Stage 3 key test expects the old baseline figures; cleaning now removes more data, so its expected range needs reviewing at Stage 3.
**Notes after finishing:** Result is 5,797 messages. The file turned out to be UTF-8, and trimming revealed 34 conflicting messages rather than 2 (decision 029). Unrecognised labels raise a `ValueError`. 13 tests pass.

## Stage 2 – Text preprocessor
**Status:** Done
**Goal:** Clean the text – raw message in, cleaned text out. Training and live checks both use it, so the model sees text cleaned the same way in both.
**In scope**, in this order (see decision 030):
1. Lowercase.
2. Remove HTML-style codes: `&amp;` becomes `&`; placeholders such as `&lt;#&gt;`, `&lt;decimal&gt;` and `&lt;time&gt;` are deleted.
3. Links become `urltoken`: `http://`, `https://` and `www.` links, plus bare domains with a common ending (such as `.com`, `.co.uk`, `.ie`).
4. Money becomes `moneytoken`: currency symbols (`£ $ € ₹`), currency words and codes (`500 pounds`, `rs.2,00,000`, `3gbp`), and pence rates (`150p`, `150ppm`).
5. Phone numbers of 7 or more digits become `phonetoken`, allowing spaces or dashes between digits.
**Out of scope:** email addresses, including their domains (left as they are); 5-digit short codes (revisit in Stage 11); `�` characters; calling this from training (Stage 3); validating input (Stage 7).
**Files:** `app/preprocessor/cleaner.py`, `app/preprocessor/__init__.py`, `tests/test_preprocessor.py`.
**Interfaces (in → out):** Clean the text: `clean_text(text)` → cleaned text (both strings), imported with `from app.preprocessor import clean_text`.
**Tests:**
- Text is lowercased.
- `&amp;` becomes `&`; placeholders are removed.
- Each form of link, money and phone number gets the right token.
- Ordering: `www.07781482378.com` gives one `urltoken`; `£1000000` gives `moneytoken`, not `phonetoken`.
- Left unchanged: email addresses, 5-digit codes, and numbers under 7 digits.
- Empty and whitespace-only text doesn't crash.
**Done when:**
- [x] `clean_text` passes all of the above
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** No HTML-style codes remain in the cleaned dataset. Tokens by message: `urltoken` 194 (12 ham), `moneytoken` 471 (16 ham), `phonetoken` 564 (6 ham). Link endings are `.com`, `.net`, `.org`, `.co.uk`, `.org.uk`, `.uk`, `.ie`, `.info`, `.biz`, `.tv` and `.ly`; `.in`, `.me` and `.co` are left out because typos such as `come.in` would count as links. 24 numbers glued to words, such as `call09050000337`, are not matched; review in Stage 11. 65 tests pass.

## Stage 3 – Training pipeline
**Status:** Done
**Goal:** train TF-IDF + logistic regression, evaluate it, save the model file.
**In scope**, in this order (see decisions 023 and 031):
1. Load the dataset and run `clean_text` on every message.
2. Remove repeats created by cleaning: keep one copy of each, and remove the 1 new conflicting message completely (expected: 5,707 messages).
3. Stratified 80/20 split with seed 42.
4. 5-fold cross-validation on the training set only, trying `C` of 0.1, 1, 10 and 100; pick the highest macro F1.
5. Train on the whole training set with that `C`: TF-IDF on words and word pairs, `min_df=2`, `sublinear_tf=True`; `LogisticRegression(class_weight="balanced", max_iter=2000)`.
6. Score once on the test set: per-class metrics, confusion matrix, macro F1, accuracy, scam-vs-safe recall and false alarm rate.
7. Save the model and its metrics.
**Out of scope:** loading the model for the app (Stage 4); the Unsure threshold and probability calibration (Stage 11); retraining to improve the test score. If the score is under the 95% target, record it and handle it in Stage 11.
**Files:** `training/train.py` (run with `python -m training.train`), `tests/test_train.py`, `models/model_v1.joblib`, `models/model_v1_metrics.json`, `requirements.txt` (pin `scikit-learn==1.9.1`).
**Interfaces (in → out):** Training writes to `models/`: the model file takes cleaned text; the metrics file holds scores and settings only, never message text.
**Tests:**
- On small made-up data: metric calculations are right; the split is repeatable; no message is in both sets; repeats and conflicts created by cleaning are removed; a saved model loads and gives the same probabilities.
- The metrics file contains no message text.
- On the real data, using cross-validation on the training portion only: scam-vs-safe recall is at least 92% and false alarms are at most 5%. This never touches the test set.
**Done when:**
- [x] Model and metrics files are saved and committed
- [x] `pytest` passes
- [x] Test-set results are recorded in these notes and in `handover.md`
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** Chosen `C` is 1. Test set (1,142 messages, used once): scam-vs-safe recall 94.9% (166 of 175), just under the 95% target; false alarms 0.3% (3 of 967); macro F1 0.893; accuracy 97.1%. Handle the shortfall in Stage 11; don't retrain for this test set.

## Stage 4 – Classifier (+ mock)
**Status:** Done
**Goal:** Classify and Load model – cleaned text in; label, probabilities and recognised-term count out (see decision 032).
**In scope:**
- `load_model(version)` returns a `Classifier`. It checks the file against its checksum, loads it, and confirms it's a usable model saved with the installed scikit-learn version. Anything wrong raises `ModelLoadError` with a clear message.
- `classifier.classify(cleaned_text)` returns a read-only `Prediction` with `label`, `probabilities` (for example `{"ham": 0.86, "spam": 0.1, "smishing": 0.04}`) and `recognised_terms`.
- `MockClassifier` has the same `classify` method and returns a fixed answer that each test sets, defaulting to ham. It needs no model file.
- `save_model` in `training/train.py` also writes the checksum, and `models/model_v1.sha256` is calculated from the existing model file. No retraining and no new test-set run.
**Out of scope:** showing Unsure when `recognised_terms` is 0 (Stage 6); explainer access to word weights (Stage 5); choosing real or mock, and loading once at startup (Stage 7).
**Files:** `app/classifier/classifier.py`, `app/classifier/mock.py`, `app/classifier/__init__.py`, `tests/test_classifier.py`, `training/train.py`, `tests/test_train.py`, `models/model_v1.sha256`.
**Interfaces (in → out):** Classify: cleaned text → `Prediction(label, probabilities, recognised_terms)`. Load model: version → `Classifier`, or `ModelLoadError`. `load_model`, `Prediction`, `MockClassifier`, `Classifier` and `ModelLoadError` are imported from `app.classifier`.
**Tests:**
- Missing, truncated, overwritten, wrong-type and wrong-version model files each raise `ModelLoadError`, and an overwritten file that would otherwise load is caught by the checksum.
- The real model file loads.
- Probabilities match the right labels and add up to 1, and `label` is the most probable class.
- `recognised_terms` is 0 for empty text and for unknown words, and more than 0 for known words.
- The real and mock classifiers return the same shape; the mock returns what the test set.
- `save_model` writes a checksum that matches the model file.
**Done when:**
- [x] `load_model`, `Classifier` and `MockClassifier` pass all of the above
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** 99 tests pass. The model file is unchanged; only its checksum was added. A mismatched scikit-learn version is refused by turning its warning into an error. Fields on `Prediction` can't be reassigned, but its `probabilities` dictionary can still be edited; nothing does this.

## Stage 5 – Explainer
**Status:** Done
**Goal:** Explain – cleaned text + prediction in, up to 3 reasons out (see decision 033).
**In scope:**
- The classifier adds `contributions` to `Prediction`: for each term in the message, how much it added to or took from each class's score (TF-IDF value × learned weight). The mock's default is empty.
- `explain(cleaned_text, prediction)` returns a list of `Reason(term, text)`:
  - **Spam or smishing:** the terms that added most to that label.
  - **Ham:** the terms that took most from ham, meaning they pointed towards spam or scam, shown as signs to be careful of. If there are none, one reason with no term: "No common scam signs found". The words that made it look legitimate are never shown.
  - Up to 3 reasons, biggest first. Only terms with a strength of at least 0.15 count, for every label. A term is skipped if it shares a word with one already chosen.
- Wording: `urltoken` → "Contains a link"; `moneytoken` → "Mentions an amount of money"; `phonetoken` → "Contains a phone number"; a word → 'Uses the word "claim"'; a pair → 'Uses the phrase "call [phone number]"'.
**Out of scope:** whether Unsure results show reasons (Stage 6); highlighting terms in the original message (Stage 8); showing the numbers to users.
**Files:** `app/explainer/explainer.py`, `app/explainer/__init__.py`, `tests/test_explainer.py`, `app/classifier/classifier.py`, `app/classifier/mock.py`, `tests/test_classifier.py`.
**Interfaces (in → out):** Classify: cleaned text → `Prediction(label, probabilities, recognised_terms, contributions)`. Explain: cleaned text + `Prediction` → list of `Reason(term, text)`. `explain` and `Reason` are imported from `app.explainer`.
**Tests:**
- Every reason's term is in the cleaned message.
- Spam and smishing reasons are the biggest contributions to that label, in order.
- Ham shows only terms that took from ham; with none, "No common scam signs found".
- Terms weaker than 0.15 are not reasons.
- No more than 3 reasons; overlapping terms are skipped.
- Each token and pair gets the right wording; our own wording never contains "safe".
- Real classifier: contributions cover exactly the message's terms; made-up examples give sensible reasons.
**Done when:**
- [x] `explain` and the new `contributions` field pass all of the above
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** 128 tests pass. Added the 0.15 minimum strength after building, because otherwise filler words became warning signs on nearly every Legitimate result (decision 033). The explainer copies the model's rule for splitting text into words, so it can check every term is in the message; if training's word-splitting changes, update the explainer to match. The classifier's usable-model check now also requires the logistic regression step.

## Stage 6 – Check service
**Status:** Done
**Goal:** Check a message – runs preprocessor → classifier → explainer and applies the Unsure rules (see decision 034).
**In scope:**
- `CheckService(classifier, threshold=UNSURE_THRESHOLD)`, where the classifier can be real or mock and `UNSURE_THRESHOLD = 0.7` is a placeholder until Stage 11.
- `service.check(message)` runs `clean_text`, then `classify`, then `explain`, and returns a read-only `CheckResult(label, confidence, status, reasons)`. The rules are applied in this order:
  1. **No recognised terms:** label `unsure`, status `no_recognised_terms`, confidence empty, no reasons.
  2. **Top probability under the threshold:** label `unsure`, status `low_confidence`, confidence is the top probability, and reasons are the explainer's reasons for the most likely label, without "No common scam signs found".
  3. **Otherwise:** label `ham`, `spam` or `smishing`, status `rated`, confidence is the top probability, and reasons as the explainer gives them.
- `app.explainer` also exports `NO_SIGNS`, so the check service can recognise that reason without reaching into the explainer.
**Out of scope:** display names such as "Legitimate" and the verify reminder (Stage 8); input validation, including empty messages (Stage 7); creating the service with the real model at startup (Stage 7); tuning the threshold (Stage 11).
**Files:** `app/check_service/service.py`, `app/check_service/__init__.py`, `tests/test_check_service.py`, `app/explainer/__init__.py`.
**Interfaces (in → out):** Check a message: text → `CheckResult(label, confidence, status, reasons)`, where reasons are the explainer's `Reason(term, text)` items. `CheckService`, `CheckResult` and `UNSURE_THRESHOLD` are imported from `app.check_service`.
**Tests:**
- Using the mock: confidence of exactly 0.7 is rated and just under is Unsure; no recognised terms gives Unsure with no confidence and no reasons, even when the top probability is high; Unsure never includes "No common scam signs found", but keeps other reasons; a rated result keeps the explainer's reasons.
- The message is cleaned before it reaches the classifier.
- Nothing is logged during a check.
- Using the real classifier on made-up messages: results have the right shape, and no result's label, status or our own reason wording contains "safe".
**Done when:**
- [x] `CheckService` passes all of the above
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** 148 tests pass. On made-up messages, an AIB-style scam (58%) and an Eir bill (48%) come out as Unsure, and the "Hi mum" scam is still ham at 91%, which the threshold can't fix (Stage 11).

## Stage 7 – REST API
**Status:** Done
**Goal:** `POST /api/check` with input validation and rate limiting (see decision 035).
**In scope:**
- `create_app(classifier=None)` in `app/__init__.py` is the app factory. With no classifier given, it loads model `v1` once at startup and creates one `CheckService`; tests pass a `MockClassifier`. If the model fails to load, the app still starts, checks return 503, and the failure is logged without any message text.
- `app/api` is a blueprint with `POST /api/check`. The request body is JSON: `{"message": "..."}`.
- Validation, in order:
  1. The body isn't a JSON object, or `message` is missing or not text → 400 `invalid_request`.
  2. `message` is empty or only spaces → 400 `empty_message`.
  3. `message` is over 1,000 characters → 400 `too_long`.
  4. Requests over 16 KB in total are refused before they're read → 413 `request_too_large`.
- Success → 200 `{"label", "confidence", "status", "reasons": [{"term", "text"}]}`, with `confidence` unrounded (`null` when nothing was recognised).
- Rate limit: 20 checks per hour per IP address on `/api/check`, using Flask-Limiter with memory storage → 429 `rate_limited`.
- Model unavailable → 503 `model_unavailable`; any other failure → 500 `internal_error`.
- Every error has the shape `{"error": {"code": "...", "message": "..."}}`, and no error ever repeats the user's text.
**Out of scope:** web pages (Stage 8); `ProxyFix` for real client IP addresses on Azure (Stage 9, see decision 013); tuning the limit (Stage 10).
**Files:** `app/__init__.py`, `app/api/__init__.py`, `app/api/routes.py`, `tests/test_api.py`.
**Interfaces (in → out):** `POST /api/check`: `{message}` → `{label, confidence, status, reasons}`, or an error as above. `create_app` is imported from `app`.
**Tests:**
- A valid request returns 200 with every field, and reasons as `{term, text}`.
- Each validation rule returns the right status and code: not JSON, not an object, missing `message`, `message` not text, empty, only spaces, 1,001 characters (1,000 is accepted), and a body over 16 KB.
- The 21st request within an hour returns 429 `rate_limited`.
- A failed model load returns 503 `model_unavailable`; an unexpected error returns 500 `internal_error`.
- The message text never appears in any response's error or in the logs, for success and for every error.
- The real model works through the API on a made-up message.
**Done when:**
- [x] `POST /api/check` passes all of the above
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** 171 tests pass. The real server's log, tested over HTTP, shows only the method, path and status code, never the message. Failed requests also count towards the rate limit. Importing anything from `app` now loads Flask, including when `training` uses the preprocessor.

## Stage 8 – Web UI
**Status:** Done
**Goal:** the home page (check a message) and the result, built to `docs/ui-design.md` (see decision 036), matching the spec at desktop width and at 390px wide with no horizontal scrolling.
**In scope:**
- A `web` blueprint with `GET /`, registered in `create_app`. It renders one page holding the home view, the checking and problem-with-input states, and the result view. The result appears in place, as the spec's motion section describes, so the message never needs to go into a URL or be stored.
- `base.html`: header, Nunito from Google Fonts, the CSS and JavaScript files.
- `index.html`: the home view, with headline, lead, privacy notice, card with label, text box, helper row, live counter, **Check message** button and three example chips; **How it works**; the checking status bar; the inline error; the result view; and the reminder row. It also holds four hidden `<template>` blocks with each result's verdict, icon, summary and "What to do" text from spec section 5, so all the wording lives in HTML.
- `styles.css`: every design token in spec section 2, exactly as written, plus typography, components, pressed states, motion, the reduced-motion, reduced-transparency and high-contrast settings, and the 900px and 600px breakpoints.
- `check.js`:
  - **Counter:** counts characters the same way as the API, so emoji count as one. `MAX` comes from `app.api.MAX_MESSAGE_LENGTH` through the template, not typed in again.
  - **Example chips:** each fills the text box with its sample message.
  - **Sending:** **Check message** sends `fetch("POST /api/check", {message})` and shows the checking state while it waits.
  - **Showing the result:** the right `<template>` is filled with the confidence, reasons and highlights from the response. The message text is only ever inserted with `textContent`, never `innerHTML`, so a message can't inject HTML.
  - **Errors:** shown inline, keeping the text and returning focus to the box. Responses are mapped to messages as shown in the table below.
  - **"Check another message":** returns to the home view.
- The message is kept only in the page's memory: no `localStorage`, `sessionStorage`, cookies or console output, and it's sent nowhere except `/api/check`.

**How the pages use `POST /api/check`:**

| Response | What the page shows |
| --- | --- |
| 200, `label` `smishing` / `spam` / `ham` | Likely scam / Marketing spam / Looks legitimate result, with "Confidence N%", meter, reasons and highlights |
| 200, `label` `unsure`, `status` `low_confidence` | Unsure result: "N%, too low to rate", with no "Closest match" line |
| 200, `label` `unsure`, `status` `no_recognised_terms` | Unsure result with no meter: "We didn't recognise enough of this message to rate it." |
| 400 `empty_message` | "**The box is empty.** …" |
| 400 `too_long` | "**That message is too long.** …" with MAX |
| 400 `invalid_request`, 413, 500, network failure | "**We couldn't check that message.** Please try again." |
| 429 `rate_limited` | "**You've checked a lot of messages.** Please wait a while and try again." |
| 503 `model_unavailable` | "**The checker isn't available right now.** Please try again later." |

**Out of scope:** new API fields (unless an open question decides otherwise); deployment (Stage 9); changes from usability testing (Stage 10); the Unsure threshold (Stage 11).
**Files:** `app/web/__init__.py`, `app/web/routes.py`, `app/web/templates/base.html`, `app/web/templates/index.html`, `app/web/static/css/styles.css`, `app/web/static/js/check.js`, `app/__init__.py` (register the blueprint), `tests/test_web.py`, `README.md` (how to run the app).
**Tests** (pytest with Flask's test client; no new dependency):
- `GET /` returns 200 with the headline, lead, privacy notice, a `<label>` linked to the `<textarea>`, `aria-describedby` for the error, the counter showing the API's MAX, three example chips, **How it works** and the reminder.
- The four result templates contain the spec's exact verdict, summary and "What to do" text; the verdict is an `<h1>`; the ham icon isn't a tick.
- No page, template, CSS or JavaScript text contains "safe".
- `styles.css` defines every token in spec section 2 with the exact value, `:focus-visible`, and the three accessibility media queries.
- `check.js` never uses `innerHTML`, `localStorage`, `sessionStorage` or `console`.
- The CSS and JavaScript files are served; `GET /` isn't rate limited; the API tests still pass.
- Each example message, sent through the real model, gives its intended result.
**Manual checks**, recorded in the notes: at desktop width (about 1280px) and at 390px wide, every state matches the spec with no horizontal scrolling; keyboard-only use works with a visible focus ring; reduced motion and high contrast settings behave as the spec says.
**Done when:**
- [x] Home and result views and all their states match the spec at desktop and at 390px, with no horizontal scrolling
- [x] Manual checks done and recorded
- [x] `pytest` passes
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions** – all answered 7 Nov 2026, where the spec didn't decide (recorded in decision 036):
1. **Unsure closest match:** no "Closest match" line, because the API doesn't return it and "Closest match: Looks legitimate" could reassure. Show "N%, too low to rate".
2. **Nothing recognised:** no meter; "We didn't recognise enough of this message to rate it."
3. **Looks legitimate with warning signs:** when the reasons include signs, the heading is "Signs to be careful of", the summary is "We found no strong scam or spam signs, but some words are worth a second look.", and the note is "Highlighted: words that are sometimes found in scams or spam." With "No common scam signs found", the spec's text stays.
4. **Unsure with no reasons:** "There were no clear signs either way."
5. **Highlighting:** only words and word pairs are highlighted; link, money and phone number reasons appear in the list but aren't highlighted. No API change.
6. **429 and 503:** the specific messages in the table above.
7. **Examples:** made-up texts with no real organisation names, reworded until Parcel fee gives Likely scam, Prize offer gives Marketing spam, and Friend running late gives Looks legitimate through the real model.
8. **Confidence:** always rounded down, so Unsure always shows under 70%, and capped at 99%.
9. **Focus ring:** `#a8432c` (4.65:1) instead of the accent (2.45:1). Meter fills stay as specified, because the percentage text carries the information.
10. **Without JavaScript:** a `<noscript>` notice that the checker needs JavaScript.
11. **Header:** on home, one nav link, "How it works", jumping to that section; on the result, "← Check another message" is a button, because it acts in place.
12. **Check another message:** clears the text box and puts focus in it.
13. **Fonts:** Nunito from Google Fonts, as the spec says.
14. **Visual check:** done by hand in the browser's dev tools at 1280px and 390px, using a checklist in the notes. No new dependency.
**Notes after finishing:**
- **Screenshots (7 Nov, by Claude):** headless Edge, driven by a throwaway script outside the repo, captured 10 states at 1280px and at a true 390px (inside a 390px frame, because headless windows won't go below about 500px). The states were home, checking, empty error, too-long error, the three examples, an Unsure (low confidence) message, the "Hi mum" text, and nothing recognised. All matched the spec, and in every state at 390px the page was exactly 390px wide with no horizontal scrolling.
- **Fixes from the screenshots:** hid the focus ring on the verdict heading, because focus moves there for screen readers but it isn't a control; and reduced the highlight padding.
- **Checked by hand (developer, 7 Nov): all good.**
  - [x] Keyboard only: Tab through home, chips, Check message, result and Check another message; the focus ring is always visible.
  - [x] Pressing a button turns it sunken immediately.
  - [x] Reduced motion (Windows: Settings → Accessibility → Visual effects → Animation effects off): no scaling, only fades.
  - [x] High contrast (`prefers-contrast: more`, in dev tools → Rendering): outlines appear on raised and sunken surfaces.
  - [x] A real phone, or dev tools device mode at 390px: no sideways scrolling.
- 226 tests pass.

## Stage 9 – Deployment
**Status:** Done
**Goal:** the app running at `https://sms-scam-detector-ie.azurewebsites.net` on Azure App Service (free tier), with message text kept out of logs and the rate limit working per user (see decision 037).
**Carried over:** add Werkzeug's `ProxyFix`, so the rate limit sees each user's real IP address instead of Azure's front end (decisions 013, 035).
**In scope:**
- **Real client address:** `create_app` uses `ProxyFix(x_for=1)` to trust the one address Azure's front end adds, and the rate limit's key removes any `:port` from it, because Azure sends `1.2.3.4:56789`.
- **Production server:** Gunicorn, configured in `gunicorn.conf.py`: 1 process (the limiter counts in memory, per process), 4 threads, port 8000, access log off. Azure starts it with `gunicorn "app:create_app()"`. Locally, `flask --app app run` stays as it is.
- **Requirements split:** `requirements.txt` holds only what the website needs (Flask, Flask-Limiter, scikit-learn, joblib, Gunicorn); `requirements-dev.txt` includes it and adds pandas and pytest. README and CLAUDE.md install with `requirements-dev.txt`.
- **Azure (run by the developer from the README):** install the Azure CLI (`winget install Microsoft.AzureCLI`), sign in, then create the resource group, the free Linux F1 plan in North Europe (Dublin) and the web app (Python 3.13, HTTPS only, build on deploy, startup command). Package only committed files with `git archive` and deploy the zip.
- **Logging:** Gunicorn's access log off; Azure's request logs and Application Insights stay off (decisions 012, 018). The app only logs errors, never message text.
- **Smoke test:** `scripts/smoke_test.py <url>`, standard library only, checks that the home page loads, HTTP redirects to HTTPS, an example gets its expected result, and an empty message gets `empty_message`. With `--rate-limit`, it also checks that the 21st check is refused, which uses up that hour's limit.
**Out of scope:** automatic deployment from GitHub; a custom domain; Application Insights (018); "Always On" (not in the free tier); usability changes (Stage 10).
**Files:** `app/__init__.py`, `gunicorn.conf.py`, `requirements.txt`, `requirements-dev.txt`, `scripts/smoke_test.py`, `tests/test_deploy.py`, `README.md`, `CLAUDE.md`.
**Interfaces (in → out):** unchanged. `gunicorn "app:create_app()"` is the production entry point.
**Tests:**
- Behind one proxy, requests with `X-Forwarded-For: 1.2.3.4:56789` and `1.2.3.4:40000` share one limit, so the 21st is refused; a different address has its own limit.
- A spoofed extra `X-Forwarded-For` entry from the user doesn't change which address is counted.
- The limit key removes the port from IPv4 and keeps IPv6 addresses intact.
- `gunicorn.conf.py` sets 1 worker and no access log.
- `requirements.txt` lists only the website's packages, with scikit-learn still pinned to 1.9.1, and `requirements-dev.txt` includes it.
- The smoke test's checks pass against a local server.
**Done when:**
- [x] Code, config and tests done; `pytest` passes
- [x] Developer has deployed with the README commands (F1 in Belgium Central; see decision 037)
- [x] Smoke test passes against the live site, including `--rate-limit` (13 Nov: all checks passed, so Azure's `:port` addresses are handled)
- [x] The live log stream shows no message text after a check (13 Nov, checked by the developer)
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:** Live at `https://sms-scam-detector-ie.azurewebsites.net` on the free F1 plan in Belgium Central. North Europe and UK South were refused because Azure for Students only allows five regions, and France Central had no free F1 quota (decision 037). 239 tests pass locally. On 13 Nov the live smoke test passed every check, including `--rate-limit` (the 21st check was refused), and the live log stream showed no message text.

## Stage 10 – Self-review and fixes
**Status:** Done
**Goal:** restyle the UI to the synth look the developer approved from a prototype (decision 039), then the developer walks through the live app with a checklist and made-up messages, on phone and laptop, and we fix what's found. User testing with other people moves to Stage 13, so it tests the finished app (decision 038).

**Part A – synth restyle** (spec: `docs/ui-design.md`, updated 14 Nov):
- **Tokens:** `styles.css` takes the new values exactly: cool grey `--base` `#e3e5e8`, deeper shadows, key faces (`--key-face`, `--accent-face`, `--key-dark`), `--radius-key`, `--focus` `#a3402a` and `--mono`.
- **Header:** no longer fixed or translucent; it scrolls away with the page.
- **Keys:** rounded squares with lit faces: coral for Check message and Check another message, charcoal for the nav keys and logo, light grey for the examples.
- **Labels:** field and section labels, the helper line and counter, the confidence label, "RESULT", step numbers and key labels are in JetBrains Mono (loaded from Google Fonts with Nunito). Reading text stays in Nunito.
- **Confidence meter:** an LED segment bar.
- **Step tiles:** big mono step numbers in `--link`.
- **Unchanged:** wording, layout, result colours, behaviour, JavaScript and the "only pressable things are raised" rule.

**Part B – self-review:** a checklist for the developer, using the made-up messages, on phone and laptop. Fixes come back as a short follow-up plan.

**Out of scope:** dark display screens, decorative hardware details (both declined, decision 039); changing wording or behaviour; user testing (Stage 13).
**Files:** `app/web/static/css/styles.css`, `app/web/templates/base.html` (font link), `tests/test_web.py`, `docs/ui-design.md`, `docs/self-review.md` (the checklist).
**Tests:**
- Every token in the updated spec is in `styles.css` with its exact value (the existing test, now reading the new spec).
- The header isn't `position: sticky` or `fixed`.
- JetBrains Mono is loaded, and `--mono` isn't used for the message panel, verdict, summary or advice.
- No `prefers-reduced-transparency` rule is left over, and the reduced-motion and high-contrast rules remain.
- All existing tests still pass, so the wording and behaviour are unchanged.
**Manual check:** screenshots of the main states at 1280px and 390px with no sideways scrolling, then the developer redeploys and looks at it live.
**Done when:**
- [x] Restyle matches the updated spec at 1280px and 390px, with no horizontal scrolling (14 Nov: 9 states screenshotted; every state exactly 390px wide)
- [x] `pytest` passes (249)
- [x] Redeployed and checked live (14 Nov, developer: "looks good")
- [x] Self-review done and its fixes made (no usability problems found, so no fixes needed)
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed
**Open questions:** none.
**Notes after finishing:**
- **Restyle:** live, and checked by the developer.
- **Self-review (developer, 14 Nov):** no usability problems on phone or laptop. Every task gave its expected result; look-and-feel and keyboard checks all passed.
- **Model findings, carried to Stage 11:** the model's reasons are faithful but often unconvincing, because it learned word statistics from an older dataset.
  - **"delivery":** appears only in scams in the training data (3.7%; no genuine delivery texts exist in it).
  - **"STOP":** appears in 16.5% of marketing spam (the UK opt-out wording).
  - **"your":** appears in 39.9% of scams and 7.1% of genuine texts.
  - **"new":** appears in 9.9% of spam.
  - **"money":** leans slightly towards genuine, and "send me" appears only in genuine texts. So the model can't recognise requests for money, which is why the "Hi mum" scam gets 91% Looks legitimate (rated **critical**).
  - **"verify":** appears in only 5 training messages.
  - **What the developer would actually notice:** a request for money, verification by text rather than email, or a prize without paying.

## Stage 11 – Tuning and evaluation
**Status:** Done
**Goal:** choose the Unsure threshold; test on Irish scam examples from public warnings; measure against targets (≥95% scam-vs-safe recall, ≤5% false alarms). Above all, deal with the Stage 10 findings, especially the "Hi mum" scam rated 91% Looks legitimate (see decision 040).

It runs in three steps, with a check-in between each:

**Step 1 – Measure (this plan):**
- **Reference set:** `data/reference_set.csv` with about 50 messages: about 25 scams, 10 marketing and 15 genuine. Columns: `id`, `text`, `expected` (`ham` / `spam` / `smishing`), `origin` (`verbatim` / `modelled` / `made_up`), `source` (a public warning URL, or `made up`), `notes`.
  - **Scams (option C, 14 Nov):** automatic collection found only 2 verbatim texts, because most warnings show examples as images or block automated reading. So the scams are a mix:
    - **Verbatim:** real texts quoted in Irish public warnings, collected by Claude and by the developer by hand.
    - **Modelled:** written by Claude, each based on a specific warning's description (source recorded), and written before any rules are designed.

    Results are reported separately for verbatim and modelled scams.
  - **Genuine:** made up, focusing on the hard cases: delivery updates, verification codes, family asking for money.
  - **Marketing:** made up, or from public examples.
- **Halves:** within each class and origin, messages are split evenly into `design` and `held_out` by the code, in a fixed order (sorted by a hash of the `id`), so the split is repeatable without a stored column. The set is frozen before step 2. Step 2 designs fixes using only the design half; the held-out half is only scored in step 3 (as in decision 023).
- **Evaluation script:** `training/evaluate_reference.py` (run with `python -m training.evaluate_reference`). It runs every message through the real `CheckService` and reports, per message and in total:
  - scams caught (any warning: Likely scam, Marketing spam or Unsure)
  - **scams shown as a confident Looks legitimate** (the dangerous failure)
  - genuine texts flagged (false alarms)
  - how often Unsure appears
  - the reasons given

  It scores only the design half unless run with `--held-out`, which is reserved for step 3.
- **Overlap check:** messages must not already be in the training data, after cleaning.

**Step 2 – Decided 14 Nov (decision 041):**
- **Unknown sender:** the app assumes every message comes from a number the user doesn't know.
- **Warning signs:** three, in a new `app/signals` package: (a) a new-number opener, (b) asks for card details, a photo of a card, or a code, (c) asks for money or a payment. Each shows as a reason and turns a confident Looks legitimate into Unsure; a sign never makes a result Likely scam on its own.
- **Clearer reasons (option B):** filler words are left out of the reasons shown.
- **Threshold:** stays at 0.7.
- **Wording:** the Looks legitimate advice and a home-page line state the unknown-sender assumption.
- **Known limitations, no change:** mostly-unrecognised text, link-only parcel scams, short codes, calibration, and over-caution on genuine texts.

**Step 3 – Build plan (approved 14 Nov, in progress):**
- **`app/signals`:** `find_signs(cleaned_text)` returns a list of `Sign(name, term, text)` from simple patterns on the cleaned text. `term` is the matched words, used for highlighting, and `text` is the reason wording:
  - `new_number`: "new / temporary / other number", "save this number", "phone broken / crashed / not working / dead / lost", "dropped my phone" → "Says it's from a new or temporary number"
  - `card_or_code`: asks for "card number / card details", "a photo of your card", or "the code" → "Asks for card details or a code"
  - `money_request`: "send me" or "transfer" with money, "pay a bill for me", "lend me", "need money" → "Asks you to send money or pay something"
  - **Must not match:** "Your verification code is 482913" (gives a code, doesn't ask for one), "Can you send me the photos", "Your new SIM has been activated".
- **Check service:**
  - after the existing "no recognised terms" rule, it runs `find_signs`
  - if the model says ham, any sign makes the result `unsure` with a new status `warning_signs` and `confidence` empty (a high ham probability next to Unsure would read as reassurance)
  - in every case, the signs come first in the reasons, followed by the explainer's, up to 3 in total
- **Explainer (option B):** a term is left out if every word in it is a filler word (`your`, `you`, `to`, `has`, `have`, `for`, `been`, `the`, `a`, `an`, `is`, `it`, `me`, `my`, `and`, `of`, `in`, `on`, `at`, `this`, `that`, `please`, `be`, `we`, `are`, `was`, `will`, `can`, `do`, `if`, `or`, `with`, `from`, `by`, `so`, `as`). So "you have" is left out, but "your order" stays.
- **API:** `status` gains the value `warning_signs`; nothing else changes.
- **Web:**
  - the Unsure template gets the line "We found warning signs, so we can't rate this message as legitimate." for `warning_signs` (no meter)
  - the Looks legitimate advice changes from "No check is perfect. If the number is unknown to you, stay cautious." to "No check is perfect. Don't send money or details to a number you don't know."
  - the helper text changes from "Paste the whole message for the best result." to "Paste the whole text from a number you don't recognise."
- **Docs:** update the interface tables (CLAUDE.md, plan, handover), `docs/ui-design.md`, and decisions 034 and 041.
- **Re-measure:** score the design half, then the **held-out half once** (`--held-out`), and record both against step 1.
- **Files:** `app/signals/__init__.py`, `app/signals/signals.py`, `app/check_service/service.py`, `app/explainer/explainer.py`, `app/web/templates/index.html`, `app/web/static/js/check.js`, tests (`test_signals.py`, plus updates to the check service, explainer, API and web tests), docs.
- **Tests:**
  - each sign's positive phrases, and the "must not match" phrases above
  - check service: ham plus a sign gives `unsure` / `warning_signs` with no confidence and the sign first; spam or scam plus a sign gives the same label with the sign first in the reasons; with no sign, the result is unchanged
  - explainer: filler-only terms are left out, mixed terms stay
  - API returns the new status
  - web: the new wording is present, and no "safe"
  - every earlier test passes, apart from the ones whose wording deliberately changes

**Original step 2 scope (kept for the record):** from the design half's results, the developer chooses: the hand-written warning signs (option C) and exactly what they do; which words to leave out of the reasons (option B); the Unsure threshold (keep 0.7, tune it, or apply it only to Legitimate results); and what to do about calibration, mostly-unrecognised text, link-only parcel scams and short codes.

**Step 3 – Fix and re-measure (separate plan):** build the chosen fixes with tests, then score both halves; the held-out half shows whether the fixes generalise.

**Out of scope:** retraining on new data (option D, declined: decision 040); user testing (Stage 13).
**Files (step 1):** `data/reference_set.csv`, `data/README.md` (sources and licence note), `training/evaluate_reference.py`, `tests/test_reference_set.py`.
**Tests (step 1):**
- The CSV loads, every `expected` label is valid, and every row has a source.
- No duplicate messages; none appear in the training data after cleaning.
- Each class is split evenly between halves, and the split is repeatable.
- The summary counts are right on a made-up set run through the mock classifier.
- The script won't score the held-out half without `--held-out`.
**Done when (step 1):**
- [x] Reference set collected, reviewed by the developer and committed (53 rows, frozen 14 Nov in `486baf5`: 8 verbatim scams, 6 of them copied by hand from Bank of Ireland's images with links replaced by a neutral link; 20 modelled scams; 10 marketing; 15 genuine)
- [x] Evaluation script and tests done; `pytest` passes (268)
- [x] Design-half results recorded in these notes (below)
- [x] Step 2 plan written

**Done when (whole stage):**
- [x] Fixes chosen, built and tested; both halves scored and recorded (307 tests pass)
- [x] Plain-English explanation given and `docs/learning_log.md` summary written
- [x] Committed and redeployed (committed 14 Nov in `8f4e8c3`; redeployed and checked live by the developer)
**Open questions:** none for step 1.
**Step 1 results – design half (27 messages, model v1, threshold 0.7, 14 Nov):**

| Group | Caught | Unsure | Missed (confident Looks legitimate) | False alarm |
| --- | --- | --- | --- | --- |
| Verbatim scams (4) | 3 | 0 | 1 | – |
| Modelled scams (10) | 5 | 3 | 2 | – |
| Marketing (5) | 4 | 1 | 0 | – |
| Genuine (8) | 3 correct | 5 | – | 0 |

- **Scams with a warning:** 11 of 14 (79%). **All 3 missed scams are family impersonation:** S02 "hey mam… save this number" (verbatim, 88% legitimate), S17 "Hi mum… new number… send me 450" (87%), and S18 "Hi Dad… temporary number… pay a bill" (89%). No threshold can fix these.
- **Genuine texts flagged as spam or scam:** none. But **5 of 8 genuine texts were Unsure** (delivery update 0.42, delivery confirmation 0.62, appointment reminder 0.41, new SIM 0.43, running late 0.68). Three of them leaned to spam or scam ("reply", "order", "your", "has been").
- **Reasons are often function words:** "your", "to", "has", "for", "been", "please".
- **Thresholds on this half:** 0.6 would cut genuine Unsure from 5 to 3 and lose no scams here, but training cross-validation showed 0.6 catches only 20 of 39 dangerous mistakes, against 28 at 0.7 (decision 034). Applying Unsure only to Legitimate results would turn 3 genuine Unsures into false alarms (G01, G08, G13).
- **Few recognised words:** every message here had 9 or more recognised terms, so this half gives no evidence on mostly-unrecognised text.

**Step 3 results (14 Nov, model v1, threshold 0.7, warning signs and filler-word clean-up added):**

| Half | Scams missed (confident Looks legitimate) | Scams with a warning | Genuine flagged as spam or scam | Genuine Unsure | Marketing caught |
| --- | --- | --- | --- | --- | --- |
| Design, before (step 1) | 3 of 14 | 11 of 14 | 0 of 8 | 5 of 8 | 4 of 5 |
| Design, after | **0 of 14** | **14 of 14** | 0 of 8 | 6 of 8 (+G06, intended) | 4 of 5 |
| Held-out, without signs (for comparison) | 1 of 14 (S19, photo of a bank card) | 13 of 14 | 0 of 7 | 5 of 7 | 4 of 5 |
| **Held-out, after (scored once)** | **0 of 14** | **14 of 14** | **0 of 7** | 5 of 7 | 4 of 5 |

- **Signs generalise:** on the held-out half, which they weren't designed on, they caught the one miss (S19, "send me a photo of your bank card") and changed no genuine result. On the design half they caught all 3 family-impersonation scams. The only other change was G06 ("Mam can you transfer me 20"), which became Unsure, as intended under the unknown-sender assumption.
- **Still a limitation:** many scams are Unsure rather than Likely scam (6 of 14 on design, 9 of 14 on held-out), and most genuine texts are Unsure (11 of 15 across both halves, including codes, a bin reminder and a bill). That's honest caution rather than reassurance, but it limits how useful the app is; recorded as a known limitation (041).
- **Reasons:** filler words are gone. Some numbers still appear as reasons ("19", from a time such as 19:25), as do weak words like "due".
- **Test set:** not re-scored. It was for the model (023), and the held-out half is what measures the warning signs.

**Notes after finishing:**
**Carried over:** the Stage 10 self-review findings above (unconvincing reasons; the model can't recognise requests for money; the "Hi mum" scam at 91% Looks legitimate is **critical**); text the model barely understands can still get a confident Looks legitimate. In Stage 10, a short non-English test sentence came out at 84% because a couple of its words are recognised, so the "no recognised terms" rule (decision 032) doesn't catch it. The app is English-only and other languages don't need supporting; the open question is whether mostly-unrecognised text should show Unsure instead of a confident result, or simply be recorded as a limitation; parcel-fee scams with only a link (no phone number) came out as Unsure at 62% and 69% in Stage 8, though that's how most current parcel scams look; the 94.9% test score (decision 031); check probability calibration; try applying the threshold only to Legitimate results (decision 034); test the "Hi mum" scam and messages with few recognised words (decisions 032, 033); review 5-digit short codes and numbers glued to words (decision 030).

## Stage 12 – Failure handling and hardening
**Status:** In progress (item 1 built, 14 Nov: 309 tests pass; screenshots at 1280px and 390px fine, with no sideways scrolling; waiting for commit and redeploy)
**Goal:** the app behaves sensibly when the model fails or gives poor output; edge cases covered by tests.

**Item 1 – Remove highlighting (decision 042):**
- **"Your message":** stays, showing the message as plain text. The highlights and the "Highlighted: …" note go, because highlighted words suggest those words are *why* a message is a scam, which isn't how the model works (Stage 10 self-review: "delivery", "new").
- **Files:** `app/web/templates/index.html` (remove the note and the ham template's `data-signs-note`), `app/web/static/js/check.js` (remove `findHighlights` and the marks; the message is inserted as plain text with `textContent`), `app/web/static/css/styles.css` (remove the `mark` and `.highlight-note` rules and the `--*-mark` tokens), `docs/ui-design.md` (remove the highlight component and the mark tokens), `tests/test_web.py`.
- **Unchanged:** the API still returns each reason's `term`. It's no longer used by the page, but removing it would change the agreed API interface for no benefit.
- **Tests:**
  - the page still has the "Your message" panel but no highlight note or `data-signs-note`
  - the script has no `findHighlights` or `mark` and still never uses `innerHTML`
  - the stylesheet has no `--*-mark` tokens or `mark` rule
  - the spec-token test still passes against the updated spec, and every other test still passes
- **Manual check:** screenshots at 1280px and 390px, then the developer redeploys.

**Item 2 – Reasons as warning signs with a "why" (decision 043; approved 15 Nov, in progress):**
- **The fixed list:** every reason comes from a fixed list of warning signs in `app/signals`. Each sign has a name, a title, a short "why it matters" and whether it can change the result. The reason text is "Title: why", for example "Contains a link: scam texts often lead to fake websites that look real." "Uses the word…" reasons disappear.

  | Sign | Found by | Can change the result? |
  | --- | --- | --- |
  | New or temporary number | existing patterns | **Yes** (041) |
  | Asks for card details or a code | existing patterns | **Yes** (041) |
  | Asks you to send money | existing patterns | **Yes** (041) |
  | Contains a link | `urltoken` | No |
  | Contains a phone number | `phonetoken` | No |
  | Mentions an amount of money | `moneytoken` | No |
  | Mentions winning or a prize | win, winner, won, prize, claim, selected, congratulations, reward | No |
  | Mentions your account or security | account, verify, login, password, suspended, restricted, locked, limited, unauthorised, device | No |
  | Mentions a payment or fee | fee, pay, payment, unpaid, charge, outstanding, refund, bill | No |
  | Creates urgency | urgent, immediately, asap, today, within N hours, expire, final notice, last chance | No |
  | Has opt-out wording (STOP) | txt/reply/text STOP, unsubscribe, opt out | No |

- **Order:** up to 3 reasons. The result-changing signs come first, then the rest in the table's order; for a spam result, the opt-out sign comes first.
- **No signs found:**
  - scam: "The wording is similar to scam texts the model learned from."
  - spam: "The wording is similar to marketing texts the model learned from."
  - Looks legitimate: "No common warning signs found" (renamed from "No common scam signs found")
  - Unsure: no reasons, so the page shows "There were no clear signs either way."
- **Explainer:** `explain(cleaned_text, prediction)` builds reasons from the signs plus these fallbacks, and no longer uses the model's word weights. `Prediction.contributions` stays in the classifier (unchanged interface) but isn't used for reasons.
- **Check service:** only the three result-changing signs can turn Looks legitimate into Unsure, as before, so every result from Stage 11 stays the same. Reasons now come only from the explainer.
- **Unchanged:** the API (reasons are still `{term, text}`) and the web page (heading logic stays the same).
- **Files:** `app/signals/signals.py`, `app/explainer/explainer.py`, `app/check_service/service.py`, tests (`test_signals.py`, `test_explainer.py`, `test_check_service.py`, plus any web or API test with old reason wording), `docs/ui-design.md`, CLAUDE.md and the plan and handover interface tables, decisions 033 and 043.
- **Tests:**
  - each new sign's words trigger it, and ordinary genuine texts don't trigger the result-changing ones
  - the reason format is "Title: why"
  - ordering and the cap of 3, including the spam rule
  - each fallback
  - no reason ever says "Uses the word"
  - "safe" never appears
  - the reference set's outcomes are identical to the Stage 11 results on both halves (only the wording changes)

**Item 2 results (15 Nov):**
- **Tests:** 314 pass.
- **Results unchanged:** reference-set outcomes are identical to Stage 11 on both halves. The held-out half was re-scored only to confirm this, with no decisions made from it.
- **Wording:** reasons now read, for example, "Contains a link: scam texts often lead to fake websites that look real." No "Uses the word…" remains, so the "19" and "due" oddities are gone too, and the optional "no plain numbers in reasons" tweak isn't needed any more.
- **Side effects:** a genuine verification code now shows "Mentions your account or security…" under Unsure, and a casual "running late" text shows no reasons ("There were no clear signs either way.").

**Item 3 – Failure handling and hardening (decision 044; plan awaiting approval):**
1. **Slow first check (cold start):**
   - after 5 seconds of checking, the status bar's text changes to "Waking up the checker, this can take up to a minute…" (still `role="status"`, so screen readers hear it)
   - after 90 seconds, the request is cancelled and the generic error shows ("We couldn't check that message. Please try again.")
   - the wording lives in the template (a `data-slow` attribute); the script uses a timer and `AbortController` to cancel
2. **Pinned versions:** `requirements.txt` pins the exact versions that pass the tests: Flask, Flask-Limiter, joblib and Gunicorn (scikit-learn is already pinned). Their own dependencies aren't pinned, which is fine for a prototype; it's noted in the decision.
3. **Security headers on every response,** added in `create_app`:
   - `Content-Security-Policy`: `default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: no-referrer`
   - `X-Frame-Options: DENY`

   The page already has no inline scripts or styles; the meter's width is set from the script, which this policy allows.
4. **Edge-case tests:**
   - emoji count the same in the counter and the API (1,000 accepted, 1,001 refused)
   - a 1,000-character word with no spaces is accepted, and the message panel wraps it (`overflow-wrap: anywhere`), with a 390px screenshot check
   - only a link, and only numbers, give a valid result
   - pasted HTML or `<script>` gives a normal result, and the page only inserts text
   - Windows line breaks (`\r\n`) are handled
5. **Health check:** `GET /health` returns 200 `{"status": "ok"}`, or 503 `{"status": "model_unavailable"}` if the model didn't load. It's not rate limited, carries no message data, and the README mentions it for waking the site before a demo.

- **Files:** `app/__init__.py` (headers, `/health`), `app/web/templates/index.html` (`data-slow`), `app/web/static/js/check.js` (timer, cancel), `requirements.txt`, `README.md`, `tests/test_hardening.py` (new), `docs/ui-design.md` (checking state), decision 044.
- **Tests:**
  - every response has the four headers, and the CSP allows exactly the sources above
  - the template has the slow-check wording; the script has the 5-second and 90-second timers and cancels the request
  - `/health` returns ok, and 503 when the model fails to load, and isn't rate limited
  - `requirements.txt` has exact pins (`==`) for all five packages
  - the edge cases above; every earlier test still passes; the reference-set results don't change
- **Manual check:** the live site still loads its fonts, scripts and styles with the new security policy (nothing blocked in the browser console), and `/health` answers.

**Item 3 results (15 Nov):**
- **Tests:** 335 pass (21 new in `tests/test_hardening.py`).
- **Security policy:** headless Chrome loaded the real page with the new policy and logged no violations; the fonts, stylesheet and script all loaded. All four headers are present, and `/health` returns `{"status": "ok"}`.
- **Pinned:** Flask 3.1.3, Flask-Limiter 4.1.1, joblib 1.6.0, Gunicorn 26.2.0, scikit-learn 1.9.1.
- **Still to do by the developer:** redeploy, then check a result live and confirm `/health` answers.

**Then:** Stage 12 is done after item 3, and Stage 13 is user testing.

## Stage 13 – User testing and final fixes
**Goal:** people unfamiliar with the app try the finished version; record where they hesitate or misread results; fix what they find (decision 038).
**Carried over from the Stage 10 discussion (13 Nov 2026), to confirm when planning:**
- **Participants:** about 5, including at least one older or less tech-confident person.
- **Sessions:** about 15 minutes each, think-aloud, on the live site on the person's own phone.
- **Tasks:** 6, each with a made-up message: scam, marketing spam, genuine, Unsure, the "Hi mum" scam (the riskiest case: "Looks legitimate" on a scam), and an empty box. After each, ask "What does this tell you?" and "What would you do now?"
- **Recording:** a notes sheet per person with no names, audio or video, plus the System Usability Scale.
- **Consent:** a short consent sheet; check with the lecturer whether ethics approval is needed.
- **Severity:** critical and serious problems get fixed; minor ones are logged.
- **Rate limit:** people on one network share 20 checks an hour, so space sessions out or use mobile data.
- **Timing:** leave a few days after the sessions for fixes before the deadline.
