"""Stage 4 tests: loading the model and classifying text."""
from dataclasses import FrozenInstanceError, asdict
import hashlib
from pathlib import Path

import joblib
import pytest
import sklearn.base

from app.classifier import Classifier, MockClassifier, ModelLoadError, Prediction, load_model

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
REAL_MODEL = MODELS_DIR / "model_v1.joblib"
LABELS = {"ham", "spam", "smishing"}


def write_model_files(directory, contents, checksum=None):
    """Write model files, using the contents' true checksum unless one is given."""
    (directory / "model_test.joblib").write_bytes(contents)
    (directory / "model_test.sha256").write_text(
        checksum or hashlib.sha256(contents).hexdigest(), encoding="utf-8"
    )


@pytest.fixture(scope="module")
def classifier():
    return load_model("v1")


def test_real_model_loads(classifier):
    assert isinstance(classifier, Classifier)


def test_missing_model_file_raises_a_clear_error(tmp_path):
    with pytest.raises(ModelLoadError, match="nosuchversion"):
        load_model("nosuchversion", tmp_path)


def test_missing_checksum_file_raises_a_clear_error(tmp_path):
    write_model_files(tmp_path, b"anything")
    (tmp_path / "model_test.sha256").unlink()
    with pytest.raises(ModelLoadError, match="Can't read"):
        load_model("test", tmp_path)


def test_overwritten_file_that_would_load_fails_the_checksum(tmp_path):
    contents = REAL_MODEL.read_bytes()
    middle = len(contents) // 2
    damaged = contents[:middle] + b"\x00" * 200 + contents[middle + 200:]
    write_model_files(tmp_path, damaged, checksum=hashlib.sha256(contents).hexdigest())

    # This is the silent case: without the checksum, the file still loads.
    assert hasattr(joblib.load(tmp_path / "model_test.joblib"), "predict_proba")
    with pytest.raises(ModelLoadError, match="checksum"):
        load_model("test", tmp_path)


def test_truncated_file_fails_the_checksum(tmp_path):
    contents = REAL_MODEL.read_bytes()
    write_model_files(
        tmp_path, contents[: len(contents) // 2], checksum=hashlib.sha256(contents).hexdigest()
    )
    with pytest.raises(ModelLoadError, match="checksum"):
        load_model("test", tmp_path)


@pytest.mark.parametrize("contents", [b"", b"this is not a model", REAL_MODEL.read_bytes()[:1000]])
def test_unreadable_file_with_a_matching_checksum_raises_a_clear_error(tmp_path, contents):
    write_model_files(tmp_path, contents)
    with pytest.raises(ModelLoadError, match="Can't load"):
        load_model("test", tmp_path)


def test_wrong_type_of_object_raises_a_clear_error(tmp_path):
    path = tmp_path / "not_a_model.joblib"
    joblib.dump({"not": "a model"}, path)
    write_model_files(tmp_path, path.read_bytes())
    with pytest.raises(ModelLoadError, match="usable"):
        load_model("test", tmp_path)


def test_model_from_another_scikit_learn_version_is_refused(tmp_path, monkeypatch):
    model = joblib.load(REAL_MODEL)
    path = tmp_path / "old.joblib"
    monkeypatch.setattr(sklearn.base, "__version__", "0.0.1")
    joblib.dump(model, path)
    monkeypatch.undo()

    write_model_files(tmp_path, path.read_bytes())
    with pytest.raises(ModelLoadError, match="Can't load"):
        load_model("test", tmp_path)


def test_probabilities_cover_every_label_and_add_up_to_1(classifier):
    prediction = classifier.classify("your account is locked verify now")
    assert set(prediction.probabilities) == LABELS
    assert sum(prediction.probabilities.values()) == pytest.approx(1)


def test_label_is_the_most_probable_class(classifier):
    prediction = classifier.classify("your account is locked verify now")
    assert prediction.probabilities[prediction.label] == max(prediction.probabilities.values())


def test_probabilities_are_matched_to_the_right_labels():
    # Fixed scores in the model's own order show each one reaches the right label.
    class FakeVectorizer:
        def transform(self, texts):
            return type("Result", (), {"nnz": 2})()

    class FakeModel:
        classes_ = ["ham", "smishing", "spam"]
        named_steps = {"tfidfvectorizer": FakeVectorizer()}

        def predict_proba(self, texts):
            return [[0.2, 0.5, 0.3]]

    prediction = Classifier(FakeModel()).classify("anything")
    assert prediction == Prediction(
        label="smishing",
        probabilities={"ham": 0.2, "smishing": 0.5, "spam": 0.3},
        recognised_terms=2,
    )


def test_probabilities_are_plain_numbers(classifier):
    prediction = classifier.classify("see you later")
    assert all(type(value) is float for value in prediction.probabilities.values())


@pytest.mark.parametrize("text", ["", "   ", "xyzzy qwertyuiop blorptastic"])
def test_no_recognised_terms_is_reported_as_0(classifier, text):
    assert classifier.classify(text).recognised_terms == 0


def test_known_words_are_counted(classifier):
    assert classifier.classify("your account is locked").recognised_terms > 0


def test_prediction_fields_cannot_be_reassigned(classifier):
    prediction = classifier.classify("see you later")
    with pytest.raises(FrozenInstanceError):
        prediction.label = "spam"


def test_real_and_mock_return_the_same_shape(classifier):
    real = classifier.classify("see you later")
    mock = MockClassifier().classify("see you later")
    assert type(real) is type(mock)
    assert set(asdict(real)) == set(asdict(mock))
    assert set(real.probabilities) == set(mock.probabilities)


def test_mock_defaults_to_ham():
    assert MockClassifier().classify("anything").label == "ham"


def test_mock_returns_what_the_test_set():
    fixed = Prediction(
        label="smishing",
        probabilities={"ham": 0.4, "spam": 0.15, "smishing": 0.45},
        recognised_terms=3,
    )
    assert MockClassifier(fixed).classify("anything") == fixed
