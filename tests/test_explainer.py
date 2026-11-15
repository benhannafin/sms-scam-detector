"""Stage 5 and 12 tests: reasons are warning signs with why they matter (decision 043)."""
import pytest

from app.classifier import Prediction, load_model
from app.explainer import NO_SIGNS, Reason, explain
from app.preprocessor import clean_text

LINK = "Contains a link: scam texts often lead to fake websites that look real."
OPT_OUT = "Has opt-out wording (STOP): this is typical of marketing texts."
SCAM_FALLBACK = "The wording is similar to scam texts the model learned from."
SPAM_FALLBACK = "The wording is similar to marketing texts the model learned from."


def make_prediction(label):
    """Reasons only depend on the label and the message, not the probabilities."""
    return Prediction(label, {"ham": 0.2, "spam": 0.3, "smishing": 0.5}, 5)


def texts(message, label):
    return [reason.text for reason in explain(clean_text(message), make_prediction(label))]


@pytest.fixture(scope="module")
def classifier():
    return load_model("v1")


def test_reasons_are_written_as_title_and_why():
    for text in texts("Verify your account now at www.bank-login.com", "smishing"):
        title, why = text.split(": ", 1)
        assert title and why.endswith(".")


def test_reasons_never_say_uses_the_word():
    message = "WINNER! You have won a £1000 prize. Call 09061701461 to claim now"
    assert not any("Uses the word" in text for text in texts(message, "smishing"))


def test_result_changing_signs_come_first():
    message = "Hi mum new number, can you send me 450 and pay at www.pay-now.com"
    assert texts(message, "smishing")[:2] == [
        "Says it's from a new or temporary number: scammers often pretend to be family or friends who've lost their phone.",
        "Asks you to send money: don't send money to a number you don't know without checking first.",
    ]


def test_no_more_than_3_reasons():
    message = "URGENT: you won a prize! Verify your account and pay the fee of €2 at www.claim.com or call 0871234567"
    assert len(texts(message, "smishing")) == 3


def test_spam_results_lead_with_the_opt_out_sign():
    message = "Win a €100 voucher at www.shop.com today. Txt STOP to end"
    assert texts(message, "spam")[0] == OPT_OUT


def test_scam_results_keep_the_list_order():
    message = "Win a €100 voucher at www.shop.com today. Txt STOP to end"
    assert texts(message, "smishing")[0] == LINK


@pytest.mark.parametrize("label, fallback", [
    ("smishing", SCAM_FALLBACK),
    ("spam", SPAM_FALLBACK),
    ("ham", NO_SIGNS.text),
])
def test_fallback_when_no_sign_is_found(label, fallback):
    assert texts("see you at the cinema", label) == [fallback]


def test_fallbacks_and_no_signs_have_no_term():
    assert explain("see you later", make_prediction("smishing"))[0].term is None
    assert NO_SIGNS == Reason(term=None, text="No common warning signs found")


def test_sign_reasons_record_the_matched_words():
    reasons = explain(clean_text("Visit www.example.com"), make_prediction("smishing"))
    assert reasons == [Reason(term="urltoken", text=LINK)]


@pytest.mark.parametrize("message", [
    "WINNER! You have won a £1000 prize. Call 09061701461 to claim now",
    "Your AIB account is locked, verify now at aib-secure.ie",
    "FreeMsg: get the latest ringtones, txt TONE to 87121, 150p/msg. Txt STOP to end",
    "Can you pick up milk on the way home?",
    "Hi mum, my phone is broken, this is my new number, can you send me money",
    "xyzzy qwertyuiop",
])
def test_real_classifier_reasons_never_say_safe(classifier, message):
    cleaned = clean_text(message)
    for reason in explain(cleaned, classifier.classify(cleaned)):
        assert "safe" not in reason.text.lower()


def test_real_classifier_gives_meaningful_scam_reasons(classifier):
    cleaned = clean_text("WINNER! You have won a £1000 prize. Call 09061701461 to claim now")
    prediction = classifier.classify(cleaned)
    assert prediction.label == "smishing"
    assert [r.text.split(":")[0] for r in explain(cleaned, prediction)] == [
        "Contains a phone number", "Mentions winning or a prize", "Mentions an amount of money",
    ]


def test_real_classifier_shows_no_signs_for_an_ordinary_text(classifier):
    cleaned = clean_text("Can you pick up milk on the way home?")
    assert explain(cleaned, classifier.classify(cleaned)) == [NO_SIGNS]
