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
| ML | `explainer` | Explain: cleaned text + prediction → up to 3 reasons (for Legitimate: signs to be careful of) |
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
| 8 | Web UI | Not started |
| 9 | Deployment (Azure App Service) | Not started |
| 10 | Usability testing and fixes | Not started |
| 11 | Tuning and evaluation | Not started |
| 12 | Failure handling and hardening | Not started |

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
**Goal:** check, result and problem-with-input pages, plus example messages.
**Key check:** matches the wireframes; works on a phone-sized screen.

## Stage 9 – Deployment
**Goal:** the app running on Azure App Service (free tier), with message text kept out of logs.
**Carried over:** add Werkzeug's `ProxyFix`, so the rate limit sees each user's real IP address instead of Azure's front end (decisions 013, 035).

## Stage 10 – Usability testing and fixes
**Goal:** people unfamiliar with the app try it; record where they hesitate or misread results; fix what they find.

## Stage 11 – Tuning and evaluation
**Goal:** choose the Unsure threshold; test on Irish scam examples from public warnings; measure against targets (≥95% scam-vs-safe recall, ≤5% false alarms).
**Carried over:** the 94.9% test score (decision 031); check probability calibration; try applying the threshold only to Legitimate results (decision 034); test the "Hi mum" scam and messages with few recognised words (decisions 032, 033); review 5-digit short codes and numbers glued to words (decision 030).

## Stage 12 – Failure handling and hardening
**Goal:** the app behaves sensibly when the model fails or gives poor output; edge cases covered by tests.
