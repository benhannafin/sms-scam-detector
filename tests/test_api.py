"""Stage 7 tests: POST /api/check."""
import logging

import pytest

import app as app_package
from app import create_app
from app.classifier import MockClassifier, ModelLoadError, Prediction

SECRET = "Your secret code is 4417 from Mary"


def scam_prediction():
    return Prediction(
        label="smishing",
        probabilities={"ham": 0.1, "spam": 0.1, "smishing": 0.8},
        recognised_terms=2,
        contributions={"urltoken": {"ham": -0.6, "spam": 0.1, "smishing": 0.5}},
    )


@pytest.fixture
def client():
    return create_app(classifier=MockClassifier(scam_prediction())).test_client()


def post(client, json=None, data=None, content_type="application/json"):
    if json is not None:
        return client.post("/api/check", json=json)
    return client.post("/api/check", data=data, content_type=content_type)


def test_valid_request_returns_every_field(client):
    response = post(client, json={"message": "Claim your prize at www.prize.com"})
    assert response.status_code == 200
    assert response.get_json() == {
        "label": "smishing",
        "confidence": 0.8,
        "status": "rated",
        "reasons": [{"term": "urltoken", "text": "Contains a link"}],
    }


def test_no_recognised_terms_gives_null_confidence():
    prediction = Prediction("ham", {"ham": 0.83, "spam": 0.1, "smishing": 0.07}, 0)
    client = create_app(classifier=MockClassifier(prediction)).test_client()
    body = post(client, json={"message": "xyzzy"}).get_json()
    assert body == {"label": "unsure", "confidence": None, "status": "no_recognised_terms", "reasons": []}


@pytest.mark.parametrize("kwargs", [
    {"data": "not json at all"},
    {"data": '{"message": "unclosed'},
    {"data": "message=hello", "content_type": "application/x-www-form-urlencoded"},
    {"json": ["a", "list"]},
    {"json": {"text": "wrong field name"}},
    {"json": {"message": 12345}},
    {"json": {"message": None}},
])
def test_malformed_requests_are_invalid(client, kwargs):
    response = post(client, **kwargs)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize("message", ["", "   ", "\n\t "])
def test_empty_message_is_refused(client, message):
    response = post(client, json={"message": message})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "empty_message"


def test_1000_characters_is_accepted(client):
    assert post(client, json={"message": "a" * 1000}).status_code == 200


def test_1001_characters_is_too_long(client):
    response = post(client, json={"message": "a" * 1001})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "too_long"


def test_request_over_16_kb_is_refused(client):
    response = post(client, json={"message": "a" * 17_000})
    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "request_too_large"


def test_21st_request_in_an_hour_is_rate_limited(client):
    for _ in range(20):
        assert post(client, json={"message": "hello"}).status_code == 200
    response = post(client, json={"message": "hello"})
    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "rate_limited"


def test_each_app_counts_from_zero():
    for _ in range(2):
        client = create_app(classifier=MockClassifier()).test_client()
        for _ in range(20):
            assert post(client, json={"message": "hello"}).status_code == 200


def test_failed_model_load_returns_503(monkeypatch, caplog):
    def broken_load(version):
        raise ModelLoadError("Model v1 failed its checksum, so the file is damaged.")

    monkeypatch.setattr(app_package, "load_model", broken_load)
    with caplog.at_level(logging.ERROR):
        client = create_app().test_client()
    assert "failed its checksum" in caplog.text

    response = post(client, json={"message": "hello"})
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "model_unavailable"


def test_unexpected_error_returns_500_and_logs_only_its_type(caplog):
    class BrokenClassifier:
        def classify(self, cleaned_text):
            raise RuntimeError(f"could not handle {cleaned_text}")

    client = create_app(classifier=BrokenClassifier()).test_client()
    with caplog.at_level(logging.DEBUG):
        response = post(client, json={"message": SECRET})
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_error"
    assert "RuntimeError" in caplog.text
    assert "secret" not in caplog.text.lower()


@pytest.mark.parametrize("message", [SECRET, SECRET + " " + "x" * 1000, "   "])
def test_message_text_never_appears_in_errors_or_logs(client, caplog, message):
    with caplog.at_level(logging.DEBUG):
        response = post(client, json={"message": message})
    body = response.get_data(as_text=True).lower()
    if response.status_code != 200:
        assert "secret" not in body
    assert "secret" not in caplog.text.lower()


def test_real_model_works_through_the_api():
    client = create_app().test_client()
    response = post(client, json={"message": "WINNER! You have won a £1000 prize. Call 09061701461 to claim now"})
    body = response.get_json()
    assert response.status_code == 200
    assert (body["label"], body["status"]) == ("smishing", "rated")
    assert body["reasons"][0] == {"term": "phonetoken", "text": "Contains a phone number"}
