"""Stage 12 tests: failure handling and hardening (decision 044)."""
from pathlib import Path
import re

import pytest

import app as app_package
from app import SECURITY_HEADERS, create_app
from app.classifier import MockClassifier, ModelLoadError

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app" / "web" / "static" / "js" / "check.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "web" / "static" / "css" / "styles.css").read_text(encoding="utf-8")


@pytest.fixture
def client():
    return create_app(classifier=MockClassifier()).test_client()


def post(client, message):
    return client.post("/api/check", json={"message": message})


# ---------- Security headers ----------

@pytest.mark.parametrize("path", ["/", "/api/check", "/health", "/assets/css/styles.css", "/no-such-page"])
def test_every_response_has_the_security_headers(client, path):
    response = client.post(path, json={"message": "hi"}) if path == "/api/check" else client.get(path)
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, (path, name)


def test_content_security_policy_allows_only_our_files_and_google_fonts():
    policy = dict(part.strip().split(" ", 1) for part in SECURITY_HEADERS["Content-Security-Policy"].split(";"))
    assert policy == {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' https://fonts.googleapis.com",
        "font-src": "https://fonts.gstatic.com",
        "img-src": "'self' data:",
        "connect-src": "'self'",
        "base-uri": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
    }
    assert "unsafe-inline" not in SECURITY_HEADERS["Content-Security-Policy"]


def test_page_has_no_inline_scripts_or_styles(client):
    # The policy blocks inline scripts and styles, so the page mustn't rely on any.
    page = client.get("/").get_data(as_text=True)
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", page)
    assert "<style" not in page
    assert not re.search(r"\sstyle=\"", page)


# ---------- Health check ----------

def test_health_is_ok_when_the_model_loaded(client):
    response = client.get("/health")
    assert (response.status_code, response.get_json()) == (200, {"status": "ok"})


def test_health_reports_a_failed_model_with_503(monkeypatch):
    def broken_load(version):
        raise ModelLoadError("Model v1 failed its checksum, so the file is damaged.")

    monkeypatch.setattr(app_package, "load_model", broken_load)
    response = create_app().test_client().get("/health")
    assert (response.status_code, response.get_json()) == (503, {"status": "model_unavailable"})


def test_health_is_not_rate_limited(client):
    for _ in range(30):
        assert client.get("/health").status_code == 200


# ---------- Slow first check ----------

def test_slow_check_wording_is_in_the_page(client):
    page = client.get("/").get_data(as_text=True)
    assert 'data-slow="Waking up the checker, this can take up to a minute…"' in page


def test_script_explains_after_5_seconds_and_gives_up_after_90():
    assert "SLOW_AFTER_MS = 5000" in JS
    assert "GIVE_UP_AFTER_MS = 90000" in JS
    assert "new AbortController()" in JS and "signal: controller.signal" in JS
    assert "clearTimeout(slowTimer)" in JS and "clearTimeout(giveUpTimer)" in JS


# ---------- Pinned versions ----------

def test_website_requirements_are_pinned_exactly():
    lines = [l.strip() for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 5
    assert all(re.fullmatch(r"[a-z-]+==\d+(\.\d+)+", line) for line in lines), lines


# ---------- Edge-case inputs ----------

def test_1000_emoji_are_accepted_and_1001_refused(client):
    # Python counts an emoji as one character, like the page's counter (Array.from).
    assert post(client, "😀" * 1000).status_code == 200
    assert post(client, "😀" * 1001).get_json()["error"]["code"] == "too_long"
    assert "Array.from(text).length" in JS


def test_one_long_word_is_accepted_and_wraps(client):
    assert post(client, "a" * 1000).status_code == 200
    assert re.search(r"\.message-panel \{[^}]*overflow-wrap: anywhere", CSS)


@pytest.mark.parametrize("message", ["www.example.com", "1234567890", "£500", "http://link-removed"])
def test_only_a_link_number_or_amount_gives_a_valid_result(message):
    client = create_app().test_client()
    body = post(client, message).get_json()
    assert body["label"] in {"ham", "spam", "smishing", "unsure"}


def test_pasted_html_is_just_text(client):
    response = post(client, '<script>alert("x")</script><b>Hi</b>')
    assert response.status_code == 200
    assert "innerHTML" not in JS and "messagePanel.textContent = message" in JS


def test_windows_line_breaks_are_handled(client):
    body = post(client, "Hi mum\r\nthis is my new number\r\n").get_json()
    assert body["status"] == "warning_signs"
