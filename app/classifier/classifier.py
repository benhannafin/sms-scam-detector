"""Load the saved model and classify cleaned text (rules in decision 032)."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import warnings

import joblib
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class ModelLoadError(Exception):
    """The model file is missing, damaged, or can't be used."""


@dataclass(frozen=True)
class Prediction:
    label: str
    probabilities: dict
    recognised_terms: int


class Classifier:
    """Classifies cleaned text using a trained model."""

    def __init__(self, model):
        self._model = model

    def classify(self, cleaned_text):
        """Return a Prediction for one cleaned message."""
        scores = self._model.predict_proba([cleaned_text])[0]
        probabilities = {
            label: float(score) for label, score in zip(self._model.classes_, scores)
        }
        vectorizer = self._model.named_steps["tfidfvectorizer"]
        return Prediction(
            label=max(probabilities, key=probabilities.get),
            probabilities=probabilities,
            recognised_terms=vectorizer.transform([cleaned_text]).nnz,
        )


def load_model(version, directory=MODELS_DIR):
    """Return a Classifier for a saved model version, or raise ModelLoadError."""
    model_path = Path(directory) / f"model_{version}.joblib"
    checksum_path = Path(directory) / f"model_{version}.sha256"

    try:
        contents = model_path.read_bytes()
        expected_checksum = checksum_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ModelLoadError(f"Can't read the files for model {version}: {error}") from error

    # Some damage still loads and gives wrong answers, so check before loading.
    if hashlib.sha256(contents).hexdigest() != expected_checksum:
        raise ModelLoadError(f"Model {version} failed its checksum, so the file is damaged.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            model = joblib.load(model_path)
    except Exception as error:
        raise ModelLoadError(f"Can't load model {version}: {error}") from error

    if not _is_usable(model):
        raise ModelLoadError(f"Model {version} isn't a usable text classifier.")
    return Classifier(model)


def _is_usable(model):
    return (
        isinstance(model, Pipeline)
        and isinstance(model.named_steps.get("tfidfvectorizer"), TfidfVectorizer)
        and hasattr(model, "predict_proba")
    )
