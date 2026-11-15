"""Check a message and apply the Unsure rules (decisions 034, 041, 043)."""
from dataclasses import dataclass

from app.explainer import explain
from app.preprocessor import clean_text
from app.signals import find_signs

# Kept at 0.7 after Stage 11 (decision 041).
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
        # Next to Unsure, only real signs are shown: a fallback such as "No common warning signs
        # found" would contradict the result.
        sign_reasons = [reason for reason in reasons if reason.term is not None]

        # Only the three result-changing signs (decision 041) can rule out Looks legitimate.
        if prediction.label == "ham" and any(s.changes_result for s in find_signs(cleaned)):
            # No confidence is shown: a high ham probability next to Unsure would read as reassurance.
            return CheckResult(label="unsure", confidence=None, status="warning_signs", reasons=sign_reasons)

        if confidence < self._threshold:
            return CheckResult(label="unsure", confidence=confidence, status="low_confidence", reasons=sign_reasons)

        return CheckResult(label=prediction.label, confidence=confidence, status="rated", reasons=reasons)
