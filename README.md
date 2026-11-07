# SMS Scam Detector

A web app that checks a pasted text message and rates it as **Legitimate**, **Marketing spam** or **Likely scam**, with a confidence level and the reasons. Low-confidence results show **Unsure**. Messages are never stored.

> Work in progress – see `plan.md` for the build plan and `docs/decisions.md` for design decisions.

## Setup (Windows, PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

`requirements.txt` holds only what the website needs (it's what Azure installs). `requirements-dev.txt` adds pandas and pytest for training and tests.

## Run the tests

```powershell
pytest
```

## Run the app

```powershell
.venv\Scripts\Activate.ps1
flask --app app run
```

Then open http://127.0.0.1:5000 in a browser. (Locally this uses Flask's development server; Azure uses Gunicorn, which doesn't run on Windows.)

## Deploy to Azure

The app runs on Azure App Service, free F1 plan, Linux, North Europe (decision 037). Live address: https://sms-scam-detector-ie.azurewebsites.net

### First time

```powershell
# 1. Install the Azure CLI once, then open a NEW PowerShell window so it's on PATH
winget install Microsoft.AzureCLI

# 2. Sign in (opens a browser)
az login

# 3. Names used below
$app  = "sms-scam-detector-ie"
$rg   = "rg-sms-scam-detector"
$plan = "plan-sms-scam-detector"

# 4. Create the resource group, the free Linux plan and the web app
az group create --name $rg --location northeurope
az appservice plan create --name $plan --resource-group $rg --sku F1 --is-linux --location northeurope
az webapp create --name $app --resource-group $rg --plan $plan --runtime "PYTHON:3.13" --startup-file gunicorn

# 5. HTTPS only, and install requirements.txt on Azure during each deploy
az webapp update --name $app --resource-group $rg --https-only true
az webapp config appsettings set --name $app --resource-group $rg --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

If `az webapp create` says the runtime isn't valid, list the available ones with `az webapp list-runtimes --os linux` and use the Python 3.13 entry.

### Deploy (first time and every update)

Only committed files are deployed, so commit first.

```powershell
git archive --format=zip --output deploy.zip HEAD
az webapp deploy --name $app --resource-group $rg --src-path deploy.zip --type zip
Remove-Item deploy.zip
```

The first deploy takes a few minutes while Azure installs the requirements.

### Check it works

```powershell
.venv\Scripts\Activate.ps1
python scripts/smoke_test.py https://sms-scam-detector-ie.azurewebsites.net
# Last: checks the 21st check is refused (uses up this hour's 20 checks)
python scripts/smoke_test.py https://sms-scam-detector-ie.azurewebsites.net --rate-limit
```

To confirm no message text reaches the logs, turn on the app's log stream, check a message in the browser, and watch:

```powershell
az webapp log config --name $app --resource-group $rg --docker-container-logging filesystem
az webapp log tail --name $app --resource-group $rg
# Ctrl+C to stop, then turn the log stream off again:
az webapp log config --name $app --resource-group $rg --docker-container-logging off
```

The free plan sleeps after about 20 minutes idle, so the first visit afterwards is slow. Open the site a minute before a demo.

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
