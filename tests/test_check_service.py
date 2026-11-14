"""Stage 6 tests: running a check and applying the Unsure rules."""
import logging

import pytest

from app.check_service import UNSURE_THRESHOLD, CheckResult, CheckService
from app.classifier import MockClassifier, Prediction, load_model
from app.explainer import NO_SIGNS, Reason


def make_prediction(label, top, recognised_terms=3, contributions=None):
    """A Prediction whose most likely label has probability `top`."""
    others = [other for other in ("ham", "spam", "smishing") if other != label]
    probabilities = {label: top, others[0]: (1 - top) / 2, others[1]: (1 - top) / 2}
    return Prediction(label, probabilities, recognised_terms, contributions or {})


def check_with(prediction, message="anything"):
    return CheckService(MockClassifier(prediction)).check(message)


@pytest.fixture(scope="module")
def real_service():
    return CheckService(load_model("v1"))


def test_threshold_placeholder_is_0_7():
    assert UNSURE_THRESHOLD == 0.7


def test_confidence_at_the_threshold_is_rated():
    result = check_with(make_prediction("smishing", 0.7))
    assert (result.label, result.status, result.confidence) == ("smishing", "rated", 0.7)


def test_confidence_just_under_the_threshold_is_unsure():
    result = check_with(make_prediction("smishing", 0.69))
    assert (result.label, result.status, result.confidence) == ("unsure", "low_confidence", 0.69)


def test_a_different_threshold_can_be_given():
    service = CheckService(MockClassifier(make_prediction("ham", 0.75)), threshold=0.8)
    assert service.check("anything").label == "unsure"


def test_no_recognised_terms_is_unsure_even_when_confident():
    result = check_with(make_prediction("ham", 0.95, recognised_terms=0))
    assert result == CheckResult(label="unsure", confidence=None, status="no_recognised_terms", reasons=[])


def test_unsure_never_says_no_common_scam_signs_found():
    # Leaning ham with no warning signs: the explainer alone would return NO_SIGNS.
    result = check_with(make_prediction("ham", 0.6, contributions={"later": {"ham": 0.2, "spam": -0.1, "smishing": -0.1}}), "see you later")
    assert result.label == "unsure"
    assert NO_SIGNS not in result.reasons
    assert result.reasons == []


def test_unsure_keeps_the_other_reasons():
    contributions = {"urltoken": {"ham": -0.6, "spam": 0.1, "smishing": 0.5}}
    result = check_with(make_prediction("smishing", 0.55, contributions=contributions), "visit www.prize.com")
    assert result.label == "unsure"
    assert result.reasons == [Reason(term="urltoken", text="Contains a link")]


def test_rated_result_keeps_the_explainer_reasons():
    result = check_with(make_prediction("ham", 0.9, contributions={"later": {"ham": 0.2, "spam": -0.1, "smishing": -0.1}}), "see you later")
    assert result.label == "ham"
    assert result.reasons == [NO_SIGNS]


def test_message_is_cleaned_before_it_reaches_the_classifier():
    received = []

    class RecordingClassifier(MockClassifier):
        def classify(self, cleaned_text):
            received.append(cleaned_text)
            return super().classify(cleaned_text)

    CheckService(RecordingClassifier()).check("WIN £500 at www.prize.com")
    assert received == ["win moneytoken at urltoken"]


def test_nothing_is_logged_during_a_check(real_service, caplog):
    with caplog.at_level(logging.DEBUG):
        real_service.check("Your account is locked, verify now at www.bank-secure.com")
    assert caplog.records == []


@pytest.mark.parametrize("message", [
    "WINNER! You have won a £1000 prize. Call 09061701461 to claim now",
    "Your AIB account is locked, verify now at aib-secure.ie",
    "FreeMsg: get the latest ringtones, txt TONE to 87121, 150p/msg",
    "Can you pick up milk on the way home?",
    "Hi mum, my phone is broken, this is my new number, can you send me money",
    "Your account is not safe, verify your details now",
    "xyzzy qwertyuiop",
    "",
])
def test_real_results_have_the_right_shape_and_never_say_safe(real_service, message):
    result = real_service.check(message)
    assert result.label in {"ham", "spam", "smishing", "unsure"}
    assert result.status in {"rated", "low_confidence", "no_recognised_terms", "warning_signs"}
    assert result.confidence is None or 0 <= result.confidence <= 1
    assert len(result.reasons) <= 3
    assert "safe" not in f"{result.label} {result.status}"
    # Our own wording; a quoted word from the message may contain "safe" (decision 033).
    for reason in result.reasons:
        own_wording = reason.text.replace(f'"{reason.term}"', "") if reason.term else reason.text
        assert "safe" not in own_wording.lower()


def test_real_scam_is_rated_likely_scam(real_service):
    result = real_service.check("WINNER! You have won a £1000 prize. Call 09061701461 to claim now")
    assert (result.label, result.status) == ("smishing", "rated")


def test_real_unknown_words_are_unsure(real_service):
    assert real_service.check("xyzzy qwertyuiop").status == "no_recognised_terms"


# ---------- Warning signs (decision 041) ----------

NEW_NUMBER = Reason(term="new number", text="Says it's from a new or temporary number")
MONEY = Reason(term="send me 450", text="Asks you to send money or pay something")


def test_legitimate_with_a_warning_sign_becomes_unsure_with_no_confidence():
    result = check_with(make_prediction("ham", 0.95), "hi this is my new number")
    assert (result.label, result.status, result.confidence) == ("unsure", "warning_signs", None)
    assert result.reasons[0] == NEW_NUMBER


def test_warning_signs_beat_low_confidence_for_a_legitimate_lean():
    result = check_with(make_prediction("ham", 0.55), "hi this is my new number")
    assert result.status == "warning_signs"


def test_warning_signs_drop_no_common_scam_signs_found():
    contributions = {"later": {"ham": 0.2, "spam": -0.1, "smishing": -0.1}}
    result = check_with(make_prediction("ham", 0.9, contributions=contributions), "new number see you later")
    assert NO_SIGNS not in result.reasons


def test_signs_come_first_on_a_scam_result_and_keep_its_label():
    contributions = {"urltoken": {"ham": -0.6, "spam": 0.1, "smishing": 0.5}}
    result = check_with(make_prediction("smishing", 0.9, contributions=contributions), "send me 450 at www.pay.com")
    assert (result.label, result.status) == ("smishing", "rated")
    assert result.reasons == [MONEY, Reason(term="urltoken", text="Contains a link")]


def test_signs_never_turn_a_result_into_likely_scam():
    result = check_with(make_prediction("ham", 0.95), "hi mum new number, send me 450")
    assert result.label != "smishing"


def test_at_most_3_reasons_with_signs():
    contributions = {w: {"ham": -0.5, "spam": 0.0, "smishing": 0.5} for w in ("aa", "bb", "cc")}
    message = "new number send me 450 aa bb cc"
    result = check_with(make_prediction("smishing", 0.9, contributions=contributions), message)
    assert len(result.reasons) == 3
    assert result.reasons[:2] == [NEW_NUMBER, MONEY]


def test_no_signs_leaves_the_result_unchanged():
    result = check_with(make_prediction("ham", 0.9), "see you later")
    assert (result.label, result.status) == ("ham", "rated")


def test_real_hi_mum_scam_is_no_longer_looks_legitimate(real_service):
    result = real_service.check("Hi mum, my phone is broken, this is my new number, can you send me money")
    assert (result.label, result.status, result.confidence) == ("unsure", "warning_signs", None)
    assert [r.text for r in result.reasons[:2]] == [
        "Says it's from a new or temporary number",
        "Asks you to send money or pay something",
    ]
