"""Stage 0 placeholder tests: check the project is set up correctly."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dataset_present():
    assert (ROOT / "data" / "sms_phishing_dataset.csv").exists()


def test_app_packages_present():
    for package in ["web", "api", "check_service", "preprocessor", "classifier", "explainer"]:
        assert (ROOT / "app" / package / "__init__.py").exists()
