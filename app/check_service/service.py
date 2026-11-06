"""Check a message and apply the Unsure rules (decision 034)."""
from dataclasses import dataclass

from app.explainer import NO_SIGNS, explain
from app.preprocessor import clean_text

# Placeholder until Stage 11 tunes it.
UNSURE_THRESHOLD = 0.7


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

        if confidence < self._threshold:
            # Next to Unsure, "No common scam signs found" could read as reassurance.
            reasons = [reason for reason in reasons if reason != NO_SIGNS]
            return CheckResult(label="unsure", confidence=confidence, status="low_confidence", reasons=reasons)

        return CheckResult(label=prediction.label, confidence=confidence, status="rated", reasons=reasons)
