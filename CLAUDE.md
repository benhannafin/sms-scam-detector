# CLAUDE.md – instructions for Claude Code

## The project
SMS Scam Detector: a Flask web app where a user pastes a text message and gets **Legitimate**, **Marketing spam** or **Likely scam**, with a confidence level and the reasons. Low-confidence results show **Unsure**. The app never says a message is "safe" and never stores messages.

At the start of every session, read `handover.md` first (current state and next action), then `plan.md` (stages) and `docs/decisions.md` (design decisions and reasoning).

At the end of every session, update `handover.md` following the instructions at the bottom of that file.

## Who decides
The developer makes all design decisions. If something is unclear, or a choice isn't already covered by `plan.md` or `docs/decisions.md`, **ask – don't decide**. Never add a dependency, change an interface, or change the architecture without asking first.

## How we work
1. Work on **one stage at a time**, as listed in `plan.md`.
2. **Before writing code for a stage**, check its section in `plan.md` is filled in and marked *In progress*. If not, help update it and wait for approval.
3. **Plan first.** Present a short plan for the stage (files, functions, interfaces, tests) and wait for approval.
4. Build only what the stage needs. No extra features.
5. Every change comes with **pytest tests**. Run `pytest` and make sure everything passes before saying a stage is done.
6. After each change, **explain in plain English** what you did and why, as if to someone new to the topic. Explain any ML or web concept used.
7. Suggest a clear commit message after each meaningful step.
8. If anything differs from the design, add or update an entry in `docs/decisions.md` (context, decision, alternatives, consequences).
9. At the end of a stage, update its status and notes in `plan.md`.

## Architecture (layered modular monolith)
One Flask app. One package per component. Packages talk **only through their interfaces** – never reach into another package's internals.

| Package | Role | Interface (in → out) |
| --- | --- | --- |
| `app/web` | Presentation: check, result and problem-with-input pages | Calls the API |
| `app/api` | REST API, input validation, rate limiting | `POST /api/check`: `{message}` → `{label, confidence, status, reasons}` |
| `app/check_service` | Runs a check; applies the Unsure rule | Check a message: text → check result |
| `app/preprocessor` | Cleans text | Clean the text: raw text → cleaned text |
| `app/classifier` | ML model (+ a mock with the same interface) | Classify: cleaned text → label + probability per class; Load model: version → model |
| `app/explainer` | Reasons behind a result | Explain: cleaned text + prediction → list of reasons |
| `training/` | Offline: trains, evaluates and saves the model | Writes `models/` |

Labels: `ham` (shown as Legitimate), `spam` (Marketing spam), `smishing` (Likely scam).
Preprocessor tokens: `urltoken`, `phonetoken`, `moneytoken`.

## Rules
- **Never write message text to disk or logs** (including error messages and debug output).
- Never use the word "safe" in any user-facing result.
- No secrets, keys or passwords in the code.
- No external AI services – the model runs inside the app.
- Keep the same interfaces between packages; if one must change, ask first and record it in `docs/decisions.md`.
- Windows development machine: give PowerShell commands.

## Commands
- Activate the environment: `.venv\Scripts\Activate.ps1`
- Install: `pip install -r requirements.txt`
- Run all tests: `pytest`

## Data
`data/sms_phishing_dataset.csv` – Mishra & Soni (2022), CC BY 4.0. Columns: `LABEL`, `TEXT`, `URL`, `EMAIL`, `PHONE`. UTF-8. Labels are spelled inconsistently ("Spam"/"spam", "Smishing"/"smishing"). Once whitespace is trimmed, 140 rows are repeats, including 34 messages with conflicting labels. Cleaned: 5,797 messages (decision 029).
