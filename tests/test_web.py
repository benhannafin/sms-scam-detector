"""Stage 8 tests: the web pages (decision 036, spec in docs/ui-design.md)."""
from html.parser import HTMLParser
from pathlib import Path
import re

import pytest

from app import create_app
from app.api import MAX_MESSAGE_LENGTH
from app.classifier import MockClassifier
from app.web import EXAMPLES

WEB_DIR = Path(__file__).resolve().parent.parent / "app" / "web"
CSS = (WEB_DIR / "static" / "css" / "styles.css").read_text(encoding="utf-8")
JS = (WEB_DIR / "static" / "js" / "check.js").read_text(encoding="utf-8")
SPEC = (Path(__file__).resolve().parent.parent / "docs" / "ui-design.md").read_text(encoding="utf-8")

RESULT_CONTENT = {
    "smishing": (
        "Likely scam",
        "This message has strong signs of a scam.",
        [
            "Don't click the link or call any number in the message.",
            "Don't reply or share any details.",
            "If you are worried, contact the organisation using a number or website you already know.",
        ],
    ),
    "spam": (
        "Marketing spam",
        "This looks like advertising: unwanted, but not a scam.",
        [
            "You can ignore or delete it.",
            "Only reply STOP if it's from a company you recognise.",
            "Never share personal or payment details by text.",
        ],
    ),
    "ham": (
        "Looks legitimate",
        "We found none of the common scam or spam signs.",
        [
            "No check is perfect. If the number is unknown to you, stay cautious.",
            "If a later message asks for money or details, check that one too.",
        ],
    ),
    "unsure": (
        "Unsure",
        "We can't tell confidently what this is, so treat it with caution.",
        [
            "Treat it with caution until you are sure who sent it.",
            "Don't call the number in the message.",
            "Contact the organisation using a number or website you already know.",
        ],
    ),
}


class PageParser(HTMLParser):
    """Collects each element's attributes and the text inside each <template>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.templates = {}
        self._template = None
        self._open = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == "template":
            self._template = attrs.get("id")
            self.templates[self._template] = []
        if self._template:
            self._open.append(tag)
            self.templates[self._template].append(("start", tag, attrs))

    def handle_endtag(self, tag):
        if tag == "template":
            self._template = None

    def handle_data(self, data):
        if self._template and data.strip():
            self.templates[self._template].append(("text", data.strip(), None))

    def find(self, tag=None, **attrs):
        return [
            a for t, a in self.elements
            if (tag is None or t == tag) and all(a.get(k.replace("_", "-")) == v for k, v in attrs.items())
        ]


@pytest.fixture(scope="module")
def client():
    return create_app(classifier=MockClassifier()).test_client()


@pytest.fixture(scope="module")
def page(client):
    return client.get("/").get_data(as_text=True)


@pytest.fixture(scope="module")
def parsed(page):
    parser = PageParser()
    parser.feed(page)
    return parser


def collapse(text):
    """Join wrapped lines, so text can be compared regardless of HTML formatting."""
    return re.sub(r"\s+", " ", text)


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


@pytest.mark.parametrize("text", [
    "Not sure about a text message?",
    "Paste it in and we'll tell you whether it looks legitimate, like marketing spam, or like a scam, and show you why.",
    "Your message is checked and then discarded. It is never stored.",
    "Paste the text message",
    "e.g. Your parcel is held. Pay the fee at…",
    "Paste the whole message for the best result.",
    "Check message",
    "Or try an example",
    "How it works",
    "Checking your message…",
    "This is an automated check and can be wrong. If a message claims to be from an organisation, contact them using a number or website you already know.",
    "Check another message",
    "The checker needs JavaScript.",
])
def test_home_page_has_the_spec_wording(page, text):
    assert text in collapse(page).replace("&#39;", "'")


def test_text_box_has_a_real_label_and_error_link(parsed):
    assert parsed.find("label", **{"for": "message"})
    textarea = parsed.find("textarea", id="message")[0]
    assert "message-error" in textarea["aria-describedby"].split()
    assert parsed.find(id="message-error")[0]["role"] == "alert"


def test_checking_status_is_announced(parsed):
    assert parsed.find(id="checking")[0]["role"] == "status"


def test_counter_uses_the_api_limit(parsed, page):
    assert parsed.find(id="counter")[0]["data-max"] == str(MAX_MESSAGE_LENGTH)
    assert f"0 / {MAX_MESSAGE_LENGTH} characters" in page


def test_three_example_chips_with_their_messages(parsed):
    chips = parsed.find("button", **{"class": "chip"})
    assert [chip["data-message"] for chip in chips] == [example["message"] for example in EXAMPLES]
    assert [example["name"] for example in EXAMPLES] == ["Parcel fee", "Prize offer", "Friend running late"]


@pytest.mark.parametrize("label", RESULT_CONTENT)
def test_result_templates_have_the_spec_wording(parsed, label):
    verdict, summary, steps = RESULT_CONTENT[label]
    parts = parsed.templates[f"result-{label}"]
    texts = [value for kind, value, _ in parts if kind == "text"]
    assert verdict in texts and summary in texts
    assert all(step in texts for step in steps)
    assert "Result" in texts
    # The verdict is the page's <h1>.
    tags = [value for kind, value, _ in parts if kind == "start"]
    assert tags.count("h1") == 1
    assert texts[texts.index("Result") + 1] == verdict


def test_spec_result_wording_matches_these_tests():
    # Guards against this test's copy of the wording drifting from the spec.
    for verdict, summary, steps in RESULT_CONTENT.values():
        assert verdict in SPEC and summary in SPEC
        assert all(step in SPEC for step in steps)


def test_legitimate_icon_is_a_speech_bubble_not_a_tick(parsed):
    paths = [attrs.get("d", "") for kind, tag, attrs in parsed.templates["result-ham"] if kind == "start" and tag == "path"]
    assert paths == ["M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.6A8 8 0 1 1 21 12z"]


@pytest.mark.parametrize("attribute, text", [
    ("data-signs-heading", "Signs to be careful of"),
    ("data-signs-summary", "We found no strong scam or spam signs, but some words are worth a second look."),
    ("data-signs-note", "Highlighted: words that are sometimes found in scams or spam."),
])
def test_legitimate_with_warning_signs_wording(parsed, attribute, text):
    assert parsed.find("template", id="result-ham")[0][attribute] == text


def test_unsure_extra_wording(parsed):
    unsure = parsed.find("template", id="result-unsure")[0]
    assert unsure["data-no-reasons"] == "There were no clear signs either way."
    assert unsure["data-not-recognised"] == "We didn't recognise enough of this message to rate it."


@pytest.mark.parametrize("code, text", [
    ("empty_message", "The box is empty. Paste the text message you want to check, then press Check message."),
    ("too_long", f"That message is too long. Paste a message of up to {MAX_MESSAGE_LENGTH} characters."),
    ("generic", "We couldn't check that message. Please try again."),
    ("rate_limited", "You've checked a lot of messages. Please wait a while and try again."),
    ("model_unavailable", "The checker isn't available right now. Please try again later."),
])
def test_error_messages(page, code, text):
    match = re.search(rf'<p data-code="{code}">(.*?)</p>', page, re.S)
    plain = collapse(re.sub(r"<[^>]+>", "", match.group(1))).replace("&#39;", "'")
    assert plain == text


def test_no_safe_anywhere_in_the_pages_styles_or_script(page):
    for text in (page, CSS, JS):
        assert not re.search(r"\bsafe\b", text, re.I)


def test_every_spec_token_is_in_the_stylesheet_with_its_exact_value():
    tokens_block = re.search(r":root \{(.*?)\n\}", SPEC, re.S).group(1)
    tokens = re.findall(r"(--[\w-]+):\s*([^;]+);", tokens_block)
    assert len(tokens) > 30
    for name, value in tokens:
        assert re.search(rf"{re.escape(name)}:\s*{re.escape(value.strip())};", CSS), name


@pytest.mark.parametrize("rule", [
    ":focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }",
    "@media (prefers-reduced-motion: reduce)",
    "@media (prefers-contrast: more)",
    "@media (max-width: 900px)",
    "@media (max-width: 600px)",
])
def test_stylesheet_has_the_required_rules(rule):
    assert rule in CSS


def test_focus_ring_uses_the_darker_colour():
    assert "--focus: #a3402a;" in CSS


def css_rules():
    """(selectors, declarations) for each rule, ignoring the @media wrappers."""
    return re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", CSS, flags=re.S))


def test_header_scrolls_away():
    for selectors, body in css_rules():
        if ".site-header" in selectors:
            assert "sticky" not in body and "fixed" not in body
            assert "backdrop-filter" not in body


def test_no_leftover_reduced_transparency_rule():
    # The header is no longer translucent (decision 039).
    assert "prefers-reduced-transparency" not in CSS


def test_mono_font_is_loaded(page):
    assert "family=JetBrains+Mono" in page


@pytest.mark.parametrize("reading_text", [".message-panel", ".verdict", ".summary", ".what-to-do", ".lead", ".headline", "textarea", "mark"])
def test_mono_is_only_for_panel_labels(reading_text):
    for selectors, body in css_rules():
        names = [name.strip() for name in selectors.split(",")]
        if "var(--mono)" in body:
            assert reading_text not in names


@pytest.mark.parametrize("forbidden", ["innerHTML", "outerHTML", "insertAdjacentHTML", "localStorage", "sessionStorage", "document.cookie", "console."])
def test_script_never_inserts_html_stores_or_logs_the_message(forbidden):
    assert forbidden not in JS


def test_stylesheet_and_script_are_served(client):
    for path in ("/assets/css/styles.css", "/assets/js/check.js"):
        assert client.get(path).status_code == 200


def test_page_links_to_its_assets_and_the_api(parsed):
    assert parsed.find("link", rel="stylesheet", href="/assets/css/styles.css")
    assert parsed.find("script", src="/assets/js/check.js")
    assert parsed.find("form", id="check-form")[0]["data-api-url"] == "/api/check"


def test_home_page_is_not_rate_limited():
    client = create_app(classifier=MockClassifier()).test_client()
    for _ in range(25):
        assert client.get("/").status_code == 200


@pytest.mark.parametrize("example", EXAMPLES, ids=[example["name"] for example in EXAMPLES])
def test_each_example_gives_its_intended_result(example):
    client = create_app().test_client()
    body = client.post("/api/check", json={"message": example["message"]}).get_json()
    assert (body["label"], body["status"]) == (example["expected_label"], "rated")
