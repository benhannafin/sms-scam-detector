"""Check that the deployed site works (decision 037). Uses only Python's standard library.

    python scripts/smoke_test.py https://sms-scam-detector-ie.azurewebsites.net
    python scripts/smoke_test.py https://sms-scam-detector-ie.azurewebsites.net --rate-limit

--rate-limit also checks that the 21st check in an hour is refused. It uses up that
hour's checks from your address, so run it last.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

# The "Parcel fee" example from the home page (a test keeps them the same).
EXAMPLE_MESSAGE = "Your package is waiting. To arrange delivery, call 0871 234 5678 now and pay the 1.50 fee to claim it."
EXAMPLE_LABEL = "smishing"
RATE_LIMIT = 20
TIMEOUT = 120  # the free tier can take a while to wake up


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, data=None, follow_redirects=True):
    """Return (status, headers, body text) without raising on error statuses."""
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
    opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=TIMEOUT) as response:
            return response.status, response.headers, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode()


def check_home(base):
    status, _, body = request(base + "/")
    return status == 200 and "Not sure about a text message?" in body, f"GET / returned {status}"


def check_https_redirect(base):
    parts = urlsplit(base)
    if parts.scheme != "https":
        return None, "skipped (not an https address)"
    status, headers, _ = request(urlunsplit(("http",) + tuple(parts[1:])) + "/", follow_redirects=False)
    location = headers.get("Location", "")
    return status in (301, 302, 307, 308) and location.startswith("https://"), f"http:// returned {status} to {location or 'nowhere'}"


def check_example(base):
    status, _, body = request(base + "/api/check", {"message": EXAMPLE_MESSAGE})
    if status != 200:
        return False, f"returned {status}: {body[:200]}"
    result = json.loads(body)
    return (result["label"], result["status"]) == (EXAMPLE_LABEL, "rated"), f"got {result['label']} ({result['status']})"


def check_empty_message(base):
    status, _, body = request(base + "/api/check", {"message": "   "})
    code = json.loads(body).get("error", {}).get("code") if body.startswith("{") else None
    return status == 400 and code == "empty_message", f"returned {status} {code}"


def check_rate_limit(base, already_sent):
    # Earlier checks in this run (and any from your browser this hour) count too.
    for sent in range(already_sent + 1, RATE_LIMIT + 6):
        status, _, _ = request(base + "/api/check", {"message": "See you at six"})
        if status == 429:
            return sent <= RATE_LIMIT + 1, f"refused at check {sent} of this run"
    return False, f"never refused after {RATE_LIMIT + 5} checks: each request may look like a new user"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="the site's address, e.g. https://sms-scam-detector-ie.azurewebsites.net")
    parser.add_argument("--rate-limit", action="store_true", help="also check the 21st check is refused")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")

    checks = [
        ("Home page loads", check_home),
        ("http:// redirects to https://", check_https_redirect),
        ("Example message gets its result", check_example),
        ("Empty message gets empty_message", check_empty_message),
    ]
    if args.rate_limit:
        checks.append(("21st check is refused", lambda b: check_rate_limit(b, already_sent=2)))

    failed = False
    for name, check in checks:
        passed, detail = check(base)
        label = "SKIP" if passed is None else "PASS" if passed else "FAIL"
        failed = failed or passed is False
        print(f"{label}  {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
