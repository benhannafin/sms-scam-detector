"""Stage 9 tests: real client addresses, server settings, requirements and the smoke test."""
import importlib.util
from pathlib import Path
import runpy
import threading

import pytest
from werkzeug.serving import make_server

from app import create_app, strip_port
from app.classifier import MockClassifier
from app.web import EXAMPLES

ROOT = Path(__file__).resolve().parent.parent
AZURE_FRONT_END = "169.254.129.5"  # requests reach the app from Azure's front end


def load_smoke_test():
    spec = importlib.util.spec_from_file_location("smoke_test", ROOT / "scripts" / "smoke_test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def post_via_azure(client, forwarded_for):
    return client.post(
        "/api/check",
        json={"message": "hello"},
        headers={"X-Forwarded-For": forwarded_for},
        environ_base={"REMOTE_ADDR": AZURE_FRONT_END},
    )


@pytest.mark.parametrize("address, expected", [
    ("1.2.3.4:56789", "1.2.3.4"),
    ("1.2.3.4", "1.2.3.4"),
    ("[2001:db8::1]:443", "2001:db8::1"),
    ("2001:db8::1", "2001:db8::1"),
    ("", ""),
])
def test_strip_port(address, expected):
    assert strip_port(address) == expected


def test_one_user_on_changing_ports_shares_one_limit():
    client = create_app(classifier=MockClassifier()).test_client()
    for port in range(40000, 40020):
        assert post_via_azure(client, f"1.2.3.4:{port}").status_code == 200
    assert post_via_azure(client, "1.2.3.4:56789").status_code == 429


def test_a_different_user_has_their_own_limit():
    client = create_app(classifier=MockClassifier()).test_client()
    for port in range(40000, 40021):
        post_via_azure(client, f"1.2.3.4:{port}")
    assert post_via_azure(client, "5.6.7.8:40000").status_code == 200


def test_a_spoofed_address_from_the_user_is_ignored():
    # The user adds their own X-Forwarded-For; Azure appends the real address after it.
    client = create_app(classifier=MockClassifier()).test_client()
    for fake in range(20):
        assert post_via_azure(client, f"9.9.9.{fake}, 1.2.3.4:{40000 + fake}").status_code == 200
    assert post_via_azure(client, "9.9.9.99, 1.2.3.4:50000").status_code == 429


def test_gunicorn_settings():
    settings = runpy.run_path(str(ROOT / "gunicorn.conf.py"))
    assert settings["wsgi_app"] == "app:create_app()"
    assert settings["workers"] == 1
    assert settings["accesslog"] is None
    assert settings["bind"] == "0.0.0.0:8000"


def read_requirements(name):
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def test_website_requirements_only():
    names = [line.split("=")[0].split(">")[0] for line in read_requirements("requirements.txt")]
    assert names == ["flask", "flask-limiter", "scikit-learn", "joblib", "gunicorn"]
    assert "scikit-learn==1.9.1" in read_requirements("requirements.txt")


def test_dev_requirements_include_the_website_ones():
    lines = read_requirements("requirements-dev.txt")
    assert lines[0] == "-r requirements.txt"
    assert any(line.startswith("pandas") for line in lines)
    assert any(line.startswith("pytest") for line in lines)


def test_smoke_test_example_matches_the_home_page():
    smoke = load_smoke_test()
    assert smoke.EXAMPLE_MESSAGE == EXAMPLES[0]["message"]
    assert smoke.EXAMPLE_LABEL == EXAMPLES[0]["expected_label"]


def test_smoke_test_passes_against_a_local_server(capsys):
    server = make_server("127.0.0.1", 0, create_app(), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        exit_code = load_smoke_test().main([f"http://127.0.0.1:{server.server_port}", "--rate-limit"])
    finally:
        server.shutdown()
    output = capsys.readouterr().out
    assert exit_code == 0, output
    assert "FAIL" not in output
    assert "PASS  21st check is refused: refused at check 21" in output
