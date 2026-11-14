"""Check a message and apply the Unsure rules (decisions 034, 041)."""
from dataclasses import dataclass

from app.explainer import NO_SIGNS, Reason, explain
from app.preprocessor import clean_text
from app.signals import find_signs

# Placeholder until Stage 11 tunes it; kept at 0.7 (decision 041).
UNSURE_THRESHOLD = 0.7
MAX_REASONS = 3


@dataclass(frozen=True)
class CheckResult:
    label: str
    confidence: float | None
    status: str
    reasons: list


class CheckService:
    """Runs a check with whichever classifier it's given (real or mock)."""

    def __init__(self, classifier, threshold=UNSURE_THRESHOLD):
        self._classifier = classifier
        self._threshold = threshold

    def check(self, message):
        """Return a CheckResult for one message. Nothing is stored or logged."""
        cleaned = clean_text(message)
        prediction = self._classifier.classify(cleaned)

        # Checked first: with no evidence, the model's answer just reflects how common each class is.
        if prediction.recognised_terms == 0:
            return CheckResult(label="unsure", confidence=None, status="no_recognised_terms", reasons=[])

        confidence = prediction.probabilities[prediction.label]
        reasons = explain(cleaned, prediction)
        # Warning signs always come first in the reasons (decision 041).
        signs = [Reason(term=sign.term, text=sign.text) for sign in find_signs(cleaned)]

        if prediction.label == "ham" and signs:
            # From an unknown sender, a sign rules out Looks legitimate. No confidence is shown,
            # because a high ham probability next to Unsure would read as reassurance.
            return CheckResult(
                label="unsure", confidence=None, status="warning_signs",
                reasons=_combine(signs, reasons),
            )

        if confidence < self._threshold:
            return CheckResult(
                label="unsure", confidence=confidence, status="low_confidence",
                reasons=_combine(signs, reasons),
            )

        return CheckResult(
            label=prediction.label, confidence=confidence, status="rated",
            reasons=_combine(signs, reasons, keep_no_signs=True),
        )


def _combine(signs, reasons, keep_no_signs=False):
    """Signs first, then the explainer's reasons, up to MAX_REASONS.

    "No common scam signs found" is only kept on a rated result: next to Unsure, or next to
    a warning sign, it would contradict the result.
    """
    drop_no_signs = bool(signs) or not keep_no_signs
    model_reasons = [r for r in reasons if not (drop_no_signs and r == NO_SIGNS)]
    return (signs + model_reasons)[:MAX_REASONS]
