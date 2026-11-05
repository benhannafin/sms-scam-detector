"""A stand-in for Classifier that needs no model file (decision 032)."""
from app.classifier.classifier import Prediction

DEFAULT_PREDICTION = Prediction(
    label="ham",
    probabilities={"ham": 1.0, "spam": 0.0, "smishing": 0.0},
    recognised_terms=1,
)


class MockClassifier:
    """Returns the same fixed Prediction for every message."""

    def __init__(self, prediction=DEFAULT_PREDICTION):
        self._prediction = prediction

    def classify(self, cleaned_text):
        return self._prediction
