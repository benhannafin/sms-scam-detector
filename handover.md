# Handover

**Read this first.** This file lets any AI assistant (or person) pick up the project with no prior context. It's updated at the end of every working session. For full detail, it points to the other files in this repo.

**Last updated:** 5 Nov 2026 · **Current stage:** 1 – Data loading and cleaning (planning, not started)

---

## 1. The project in brief

**SMS Scam Detector** is a Flask web app. A user pastes a text message and gets one of three results – **Legitimate**, **Marketing spam** or **Likely scam** – with a confidence level and the reasons (highlighted words and signals). If the model isn't confident enough, it shows **Unsure**. It never says a message is "safe", never stores messages, and always reminds the user to verify with the organisation directly.

- **ML approach:** TF-IDF text features + class-weighted logistic regression, trained on one public dataset.
- **Architecture:** layered modular monolith – one Flask app, one package per component, packages talk only through defined interfaces.
- **Hosting:** Microsoft Azure App Service (free tier for the prototype).
- **Context:** built as a solo university project (an AI prototype for an application architecture module), so clear structure, tests and explainable code matter.

## 2. How to work with the developer – important

- **The developer makes every decision.** If a choice isn't already recorded in `plan.md` or `docs/decisions.md`, ask – don't decide. Offer options with a suggestion, then wait.
- **Explain everything simply.** The developer wants to understand every part of the code. Break things down in plain English, as if new to the topic; explain ML and web concepts; skip universal basics (they have decent technical knowledge).
- **One stage at a time.** Plan the stage in `plan.md` first, get approval, then build. No extra features.
- **Tests for everything.** `pytest` must pass before a stage is done.
- **Record design changes** in `docs/decisions.md`.
- **Developer's machine:** Windows, PowerShell, VS Code, Claude Code.

## 3. Where everything is

| File | What it holds |
| --- | --- |
| `handover.md` | This file – current state and next steps |
| `plan.md` | Architecture summary, conventions, workflow, all stages with status and detail |
| `docs/decisions.md` | Architecture decision record: 28 decisions with context, alternatives and consequences |
| `CLAUDE.md` | Standing instructions for Claude Code (also useful for any AI) |
| `docs/learning_log.md` | Developer's own summaries after each stage |
| `README.md` | Setup and run instructions |
| `data/README.md` | Dataset source, licence and known issues |

## 4. Architecture at a glance

| Package | Role | Interface (in → out) |
| --- | --- | --- |
| `app/web` | Check, result and problem-with-input pages | Calls the API |
| `app/api` | REST API, input validation, rate limiting | `POST /api/check`: `{message}` → `{label, confidence, status, reasons}` |
| `app/check_service` | Runs a check, applies the Unsure rule | Check a message: text → check result |
| `app/preprocessor` | Cleans text | Clean the text: raw text → cleaned text |
| `app/classifier` | ML model + a mock with the same interface | Classify: cleaned text → label + class probabilities; Load model: version → model |
| `app/explainer` | Reasons behind a result | Explain: cleaned text + prediction → reasons |
| `training/` | Offline training, evaluation, saving the model | Writes `models/` |

Designed but **not built** (target design only): feedback API (`POST /api/feedback`), feedback service and store, scheduled human-approved retraining, Application Insights monitoring.

## 5. Key facts you'll need

**Dataset:** `data/sms_phishing_dataset.csv` – Mishra & Soni (2022), CC BY 4.0. 5,971 messages: 4,844 ham, 638 smishing, 489 spam. Columns `LABEL`, `TEXT`, `URL`, `EMAIL`, `PHONE`.
- Labels spelled inconsistently ("Spam"/"spam", "Smishing"/"smishing")
- 22 exact duplicate messages; 2 messages appear with conflicting labels
- Not UTF-8 – £ signs garble unless read with a Western encoding (likely `latin-1`; to be confirmed in Stage 1)
- Some messages start with a tab character
- Many spam/smishing texts are older UK messages; others were collected in India

**Baseline results** (exploratory run, before the repo existed; 80/20 stratified split, seed 42, 1,190 test messages):

| Model | Smishing recall | Spam recall | Macro F1 | Accuracy |
| --- | --- | --- | --- | --- |
| Always "ham" | 0% | 0% | – | 81.3% |
| Naive Bayes | 73.8% | 44.3% | 0.791 | 92.7% |
| Logistic regression (chosen) | 88.1% | 78.4% | 0.892 | 96.6% |
| Linear SVM | 88.9% | 79.4% | 0.903 | 97.1% |

Logistic regression: 96.0% scam-vs-safe recall (214/223 spam+smishing not rated ham), 0.4% false alarms (4/967). Most errors confuse spam with smishing; only 1 of 126 smishing texts was rated ham. Settings used: TF-IDF on words + word pairs, `min_df=2`, `sublinear_tf=True`; `LogisticRegression(class_weight="balanced", C=10, max_iter=2000)`. That run kept one copy of each conflicting message instead of removing them – Stage 1 fixes this.

**Targets:** ≥95% scam-vs-safe recall; ≤5% false alarms on genuine texts.

## 6. Environment setup

```powershell
py -m venv .venv            # 'python' isn't on PATH on the dev machine; use 'py' for this step
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

## 7. Current status

| # | Stage | Status |
| --- | --- | --- |
| 0 | Project setup | Done (repo created, env working, 2 tests passing, pushed) |
| 1 | Data loading and cleaning | **Planning – waiting on developer's decisions** |
| 2–12 | Preprocessor → classifier → explainer → check service → API → web UI → deploy → usability → tuning → hardening | Not started |

## 8. Next action

Finish planning **Stage 1** and write its section in `plan.md`. The developer needs to decide five things (suggestions in brackets):

1. Where the code lives (`training/data.py` – the web app never loads the dataset)
2. File encoding (`latin-1`; verify £ reads correctly)
3. Trim whitespace from labels and messages before deduplicating (yes)
4. Drop the dataset's URL/EMAIL/PHONE columns (yes – the preprocessor detects these itself, and live messages won't have them)
5. Clean in code on every load rather than saving a cleaned CSV (yes)

Then: write the Stage 1 section in `plan.md`, plan the code with Claude Code, build, test, explain, commit.

## 9. Open questions and pending decisions

- **Stage 1 decisions** – see section 8.
- **"Proposed" entries in `docs/decisions.md`** (017, 018, 022, 023, 024) – suggested details the developer hasn't confirmed: Azure Blob/SQL storage, Application Insights, data cleaning rules, 5-fold cross-validation, reference-set check after retraining.
- **Decision 028 (Open)** – user feedback labels may be unreliable because users often don't know the truth. Suggested: ask "How do you know?" and retrain mainly on verified public-warning examples.
- **Optional later experiment** – compare against a fine-tuned DistilBERT model.

## 10. Session log

Newest first. One entry per session: what was done, what was decided, what's next.

| Date | Summary |
| --- | --- |
| 5 Nov 2026 | Repo `sms-scam-detector` created from the starter (structure, CLAUDE.md, plan.md, decisions.md, dataset, tests). Python is installed but not on PATH – `py` used to create the venv. 2 tests pass; pushed. Stage 1 planning started; five decisions pending. `handover.md` added. |
| Before 5 Nov | Project chosen and designed: dataset explored, baseline models trained, architecture, risks, test approach and wireframes designed, 28 decisions recorded. |

---

## How to update this file (end of every session)

1. Update **Last updated** and **Current stage** at the top.
2. Update **Current status** (section 7) and **Next action** (section 8).
3. Add or remove items in **Open questions** (section 9).
4. Add a new row at the top of the **Session log** (section 10).
5. If key facts changed (new results, new dataset findings), update section 5.
6. Commit with the message `Update handover`.
