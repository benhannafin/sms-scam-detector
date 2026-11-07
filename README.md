# SMS Scam Detector

A web app that checks a pasted text message and rates it as **Legitimate**, **Marketing spam** or **Likely scam**, with a confidence level and the reasons. Low-confidence results show **Unsure**. Messages are never stored.

> Work in progress – see `plan.md` for the build plan and `docs/decisions.md` for design decisions.

## Setup (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the tests

```powershell
pytest
```

## Run the app

```powershell
.venv\Scripts\Activate.ps1
flask --app app run
```

Then open http://127.0.0.1:5000 in a browser.

## Project structure

| Folder | Purpose |
| --- | --- |
| `app/web` | Web pages |
| `app/api` | REST API (`POST /api/check`) |
| `app/check_service` | Runs a check, applies the Unsure rule |
| `app/preprocessor` | Cleans message text |
| `app/classifier` | The ML model (+ a mock) |
| `app/explainer` | Reasons behind a result |
| `training/` | Trains and saves the model |
| `models/` | Saved model files |
| `data/` | Dataset |
| `tests/` | Automated tests |
| `docs/` | Decisions and learning log |

## Data

SMS Phishing Dataset for Machine Learning and Pattern Recognition – Mishra, S. and Soni, D. (2022), Mendeley Data, doi: 10.17632/f45bkkt8pr.1. Licensed CC BY 4.0.
