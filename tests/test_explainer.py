"""Stage 5 tests: turning a prediction into reasons."""
import pytest

from app.classifier import Prediction, load_model
from app.explainer import Reason, explain
from app.preprocessor import clean_text


def make_prediction(label, contributions):
    """A Prediction with made-up contributions; probabilities don't affect reasons."""
    return Prediction(
        label=label,
        probabilities={"ham": 0.2, "spam": 0.3, "smishing": 0.5},
        recognised_terms=len(contributions),
        contributions={
            term: {"ham": scores[0], "spam": scores[1], "smishing": scores[2]}
            for term, scores in contributions.items()
        },
    )


@pytest.fixture(scope="module")
def classifier():
    return load_model("v1")


def test_scam_reasons_are_the_biggest_contributions_in_order():
    prediction = make_prediction("smishing", {
        "claim": (-0.5, 0.1, 0.6),
        "urltoken": (-0.6, 0.2, 0.8),
        "prize": (-0.3, 0.2, 0.4),
        "later": (0.3, 0.0, 0.1),
    })
    reasons = explain("claim your prize at urltoken later", prediction)
    assert [r.term for r in reasons] == ["urltoken", "claim", "prize"]


def test_spam_reasons_use_the_spam_scores():
    prediction = make_prediction("spam", {
        "txt": (-0.4, 0.5, 0.1),
        "claim": (-0.4, 0.2, 0.6),
    })
    assert [r.term for r in explain("txt to claim", prediction)] == ["txt", "claim"]


def test_terms_weaker_than_the_minimum_are_not_reasons():
    prediction = make_prediction("smishing", {"urltoken": (-0.6, 0.0, 0.8), "is": (-0.1, 0.0, 0.1)})
    assert [r.term for r in explain("is urltoken", prediction)] == ["urltoken"]


def test_legitimate_with_only_weak_signs_says_no_signs():
    prediction = make_prediction("ham", {"on": (-0.14, 0.07, 0.07), "the": (-0.04, 0.02, 0.02)})
    assert explain("on the way", prediction) == [Reason(term=None, text="No common scam signs found")]


def test_terms_that_pointed_away_from_the_label_are_not_reasons():
    prediction = make_prediction("smishing", {"urltoken": (-0.6, 0.0, 0.8), "pay": (0.1, 0.0, -0.1)})
    assert [r.term for r in explain("pay at urltoken", prediction)] == ["urltoken"]


def test_no_more_than_3_reasons():
    prediction = make_prediction("smishing", {
        word: (-0.1, 0.0, 0.1 * i) for i, word in enumerate(["aa", "bb", "cc", "dd", "ee"], 1)
    })
    assert len(explain("aa bb cc dd ee", prediction)) == 3


def test_terms_overlapping_one_already_chosen_are_skipped():
    prediction = make_prediction("smishing", {
        "phonetoken": (-0.6, 0.0, 0.9),
        "call phonetoken": (-0.5, 0.0, 0.8),
        "claim": (-0.4, 0.0, 0.5),
    })
    assert [r.term for r in explain("call phonetoken to claim", prediction)] == ["phonetoken", "claim"]


def test_legitimate_shows_only_terms_that_took_from_ham():
    prediction = make_prediction("ham", {
        "my": (0.33, -0.2, -0.13),
        "new": (-0.2, 0.15, 0.05),
        "send": (-0.15, 0.05, 0.1),
    })
    reasons = explain("my new number send me", prediction)
    assert [r.term for r in reasons] == ["new", "send"]


def test_legitimate_with_no_warning_signs_says_so():
    prediction = make_prediction("ham", {"later": (0.2, -0.1, -0.1)})
    assert explain("see you later", prediction) == [Reason(term=None, text="No common scam signs found")]


def test_scam_with_no_supporting_terms_gives_no_reasons():
    assert explain("anything", make_prediction("smishing", {})) == []


def test_every_reason_term_is_in_the_message():
    prediction = make_prediction("smishing", {"urltoken": (-0.6, 0.0, 0.8), "prize": (-0.3, 0.0, 0.4)})
    assert [r.term for r in explain("visit urltoken today", prediction)] == ["urltoken"]


@pytest.mark.parametrize("term, text", [
    ("urltoken", "Contains a link"),
    ("moneytoken", "Mentions an amount of money"),
    ("phonetoken", "Contains a phone number"),
    ("claim", 'Uses the word "claim"'),
    ("to claim", 'Uses the phrase "to claim"'),
    ("call phonetoken", 'Uses the phrase "call [phone number]"'),
    ("moneytoken prize", 'Uses the phrase "[amount of money] prize"'),
])
def test_wording(term, text):
    prediction = make_prediction("smishing", {term: (-0.5, 0.0, 0.5)})
    assert explain(term, prediction) == [Reason(term=term, text=text)]


@pytest.mark.parametrize("message", [
    "WINNER! You have won a £1000 prize. Call 09061701461 to claim now",
    "Your AIB account is locked, verify now at aib-secure.ie",
    "FreeMsg: get the latest ringtones, txt TONE to 87121, 150p/msg",
    "See you at the cinema later, will text when I get there",
    "Hi mum, my phone is broken, this is my new number, can you send me money",
    "xyzzy qwertyuiop",
])
def test_real_classifier_reasons_are_from_the_message_and_never_say_safe(classifier, message):
    cleaned = clean_text(message)
    reasons = explain(cleaned, classifier.classify(cleaned))
    assert 1 <= len(reasons) <= 3
    for reason in reasons:
        assert reason.term is None or reason.term in cleaned
        assert "safe" not in reason.text.lower()


def test_real_classifier_gives_sensible_scam_reasons(classifier):
    cleaned = clean_text("WINNER! You have won a £1000 prize. Call 09061701461 to claim now")
    terms = [r.term for r in explain(cleaned, classifier.classify(cleaned))]
    assert terms == ["phonetoken", "claim", "prize"]


def test_real_classifier_shows_warning_signs_for_the_hi_mum_scam(classifier):
    cleaned = clean_text("Hi mum, my phone is broken, this is my new number, can you send me money")
    prediction = classifier.classify(cleaned)
    assert prediction.label == "ham"
    assert [r.term for r in explain(cleaned, prediction)] == ["new", "send"]


def test_real_classifier_shows_no_signs_for_an_ordinary_text(classifier):
    cleaned = clean_text("Can you pick up milk on the way home?")
    assert explain(cleaned, classifier.classify(cleaned)) == [
        Reason(term=None, text="No common scam signs found")
    ]
