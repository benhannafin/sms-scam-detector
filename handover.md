# Handover

**Read this first.** This file lets any AI assistant (or person) pick up the project with no prior context. It's updated at the end of every working session. For full detail, it points to the other files in this repo.

**Last updated:** 6 Nov 2026 · **Current stage:** 6 – Check service (not started)

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
| `docs/decisions.md` | Architecture decision record: 33 decisions with context, alternatives and consequences |
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
| `app/classifier` | ML model + a mock with the same interface | Classify: cleaned text → label + class probabilities + recognised-term count + term contributions; Load model: version → model |
| `app/explainer` | Reasons behind a result | Explain: cleaned text + prediction → up to 3 reasons (for Legitimate: signs to be careful of) |
| `training/` | Offline training, evaluation, saving the model | Writes `models/` |

Designed but **not built** (target design only): feedback API (`POST /api/feedback`), feedback service and store, scheduled human-approved retraining, Application Insights monitoring.

## 5. Key facts you'll need

**Dataset:** `data/sms_phishing_dataset.csv` – Mishra & Soni (2022), CC BY 4.0. 5,971 messages: 4,844 ham, 638 smishing, 489 spam. Columns `LABEL`, `TEXT`, `URL`, `EMAIL`, `PHONE`.
- Labels spelled inconsistently ("Spam"/"spam", "Smishing"/"smishing")
- UTF-8 – reading it as `latin-1` garbles every £ into Â£. It also contains 185 `�` characters that can't be recovered
- 161 messages start with whitespace (153 with a tab), which hides repeats. After trimming: 140 repeated rows, including 34 messages labelled both spam and smishing (before trimming it looks like only 22 and 2)
- Cleaned dataset (decision 029): 5,797 messages – 4,834 ham, 528 smishing, 435 spam
- Many spam/smishing texts are older UK messages; others were collected in India

**Stage 3 model** (`models/model_v1.joblib`, `C=1`; 5,707 messages after removing repeats; test set of 1,142 messages, used once – don't tune against it):

| Scam-vs-safe recall | False alarms | Macro F1 | Accuracy | Smishing recall | Spam recall |
| --- | --- | --- | --- | --- | --- |
| 94.9% (166/175) – just under the target | 0.3% (3/967) | 0.893 | 97.1% | 88.6% | 77.0% |

**Baseline results** (superseded by the above; exploratory run, before the repo existed; 80/20 stratified split, seed 42, 1,190 test messages):

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
| 1 | Data loading and cleaning | Done (`training/data.py`, 13 tests passing, pushed) |
| 2 | Text preprocessor | Done (`app/preprocessor`, 65 tests passing, pushed) |
| 3 | Training pipeline | Done (`training/train.py`, `models/model_v1.joblib`, 76 tests passing, pushed) |
| 4 | Classifier (+ mock) | Done (`app/classifier`, 99 tests passing, pushed) |
| 5 | Explainer | Done (`app/explainer`, 128 tests passing, pushed) |
| 6–12 | Check service → API → web UI → deploy → usability → tuning → hardening | Not started |

## 8. Next action

Plan **Stage 6** (check service): fill in its section in `plan.md`, get approval, then build. It must show Unsure when `recognised_terms` is 0 (decision 032), and needs decisions on the Unsure threshold placeholder until Stage 11, and on whether Unsure results show reasons.

## 9. Open questions and pending decisions

- **Phone numbers glued to words** – 24 cases such as `call09050000337` aren't matched by `phonetoken`, all in spam or smishing. Left as they are for now; can be reviewed in Stage 11.
- **"Hi mum" scam rated Legitimate** – a made-up "Hi mum, my phone is broken, this is my new number, can you send me money" text came out as ham at 91%. This is a common real scam, so include it in the Stage 11 Irish check.
- **95% target** – the test score is 94.9% scam-vs-safe recall, just under the target. Handle it in Stage 11 (decision 031), not by retraining for this test set.
- **"Proposed" entries in `docs/decisions.md`** (017, 018, 024) – suggested details the developer hasn't confirmed: Azure Blob/SQL storage, Application Insights, reference-set check after retraining.
- **Decision 028 (Open)** – user feedback labels may be unreliable because users often don't know the truth. Suggested: ask "How do you know?" and retrain mainly on verified public-warning examples.
- **Optional later experiment** – compare against a fine-tuned DistilBERT model.

## 10. Session log

Newest first. One entry per session: what was done, what was decided, what's next.

| Date | Summary |
| --- | --- |
| 6 Nov 2026 | Stage 5 done: explainer built. Legitimate results show only signs to be careful of, or "No common scam signs found", after the "Hi mum" scam came out as ham because of `my` and `me`. Terms under 0.15 are dropped. Reasons may quote message words containing "safe" (decision 033). Next: plan Stage 6. |
| 5 Nov 2026 | Stage 4 done: classifier and mock built. Added a recognised-term count, because text with no known words came out as 83% ham, and a model checksum, because some damaged files load normally (decision 032). So far the developer has asked Claude to draft each learning log entry. Next: plan Stage 5. |
| 5 Nov 2026 | Stage 3 done: model v1 trained on 5,707 messages after removing repeats created by cleaning (decisions 023, 031). Test set used once: 94.9% scam-vs-safe recall, just under the target, and 0.3% false alarms. scikit-learn pinned to 1.9.1. Next: plan Stage 4. |
| 5 Nov 2026 | Stage 2 done: `clean_text()` built and tested. HTML-style codes appeared only in ham, so they are now removed to stop the model using them as a shortcut (decision 030). Next: plan Stage 3. |
| 5 Nov 2026 | Stage 1 done: `load_dataset()` built and tested. Checking the real file showed it's UTF-8 and that trimming reveals 34 conflicting messages; all removed, leaving 5,797 messages (decision 029, replacing 022). `handover.md` now tracked. Next: plan Stage 2. |
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
