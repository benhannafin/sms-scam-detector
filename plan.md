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
| ML | `classifier` | Classify: cleaned text → label + probability per class + recognised-term count; Load model: version → model |
| ML | `explainer` | Explain: cleaned text + prediction → list of reasons |
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
| 5 | Explainer | Not started |
| 6 | Check service | Not started |
| 7 | REST API | Not started |
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
**Goal:** Explain – cleaned text + prediction in, reasons out.
**Key test:** every reason refers to something actually in the message.

## Stage 6 – Check service
**Goal:** Check a message – runs preprocessor → classifier → explainer and applies the Unsure rule.
**Key tests:** low confidence returns Unsure; no recognised terms returns Unsure (decision 032); "safe" never appears in a result.

## Stage 7 – REST API
**Goal:** `POST /api/check` with input validation and rate limiting.
**Key tests:** empty, over-long and malformed input return clear errors; requests beyond the limit are refused; valid requests return all fields.

## Stage 8 – Web UI
**Goal:** check, result and problem-with-input pages, plus example messages.
**Key check:** matches the wireframes; works on a phone-sized screen.

## Stage 9 – Deployment
**Goal:** the app running on Azure App Service (free tier), with message text kept out of logs.

## Stage 10 – Usability testing and fixes
**Goal:** people unfamiliar with the app try it; record where they hesitate or misread results; fix what they find.

## Stage 11 – Tuning and evaluation
**Goal:** choose the Unsure threshold; test on Irish scam examples from public warnings; measure against targets (≥95% scam-vs-safe recall, ≤5% false alarms).

## Stage 12 – Failure handling and hardening
**Goal:** the app behaves sensibly when the model fails or gives poor output; edge cases covered by tests.
