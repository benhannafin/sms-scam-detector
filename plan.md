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
| ML | `classifier` | Classify: cleaned text → label + probability per class; Load model: version → model |
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
| 2 | Text preprocessor | Not started |
| 3 | Training pipeline | Not started |
| 4 | Classifier (+ mock) | Not started |
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
**Goal:** Clean the text – raw message in, cleaned text out.
**Key points:** lowercase; replace links, phone numbers and money amounts with `urltoken`, `phonetoken`, `moneytoken`.
**Key tests:** each token replacement works; empty text doesn't crash.

## Stage 3 – Training pipeline
**Goal:** train TF-IDF + logistic regression, evaluate it, save the model file.
**Key points:** stratified 80/20 split with a fixed seed; cross-validation on training data only; report per-class metrics, confusion matrix, scam-vs-safe recall and false alarm rate.
**Key test:** reproduces the baseline (~96% scam-vs-safe recall, ~0.4% false alarms).

## Stage 4 – Classifier (+ mock)
**Goal:** Classify and Load model – cleaned text in, label + probabilities out.
**Key points:** a mock classifier with the same interface, so implementations can be swapped in one place.
**Key tests:** missing or damaged model file gives a clear error, not a crash; mock and real return the same result shape.

## Stage 5 – Explainer
**Goal:** Explain – cleaned text + prediction in, reasons out.
**Key test:** every reason refers to something actually in the message.

## Stage 6 – Check service
**Goal:** Check a message – runs preprocessor → classifier → explainer and applies the Unsure rule.
**Key tests:** low confidence returns Unsure; "safe" never appears in a result.

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
