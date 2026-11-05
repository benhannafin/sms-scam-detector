"""Train, evaluate and save the model (rules in decisions 023 and 031).

Run with: python -m training.train
"""
import hashlib
import json
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import make_pipeline

from app.preprocessor import clean_text
from training.data import load_dataset, remove_conflicts_and_duplicates

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_VERSION = "v1"
SEED = 42
C_VALUES = [0.1, 1, 10, 100]
LABELS = ["ham", "spam", "smishing"]


def prepare_data(data):
    """Clean every message, then remove the repeats and conflicts that cleaning creates."""
    cleaned = data.assign(text=data["text"].map(clean_text))
    return remove_conflicts_and_duplicates(cleaned)


def split_data(data):
    """Return a repeatable, stratified 80/20 split as (train, test)."""
    return train_test_split(data, test_size=0.2, stratify=data["label"], random_state=SEED)


def build_model(c):
    """Return an untrained TF-IDF + class-weighted logistic regression pipeline."""
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(class_weight="balanced", C=c, max_iter=2000),
    )


def cross_validate(train, c):
    """Return a prediction for each training message from a model that didn't learn from it."""
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    return cross_val_predict(build_model(c), train["text"], train["label"], cv=folds)


def choose_c(train):
    """Return the C with the highest macro F1, plus the score for each C tried."""
    scores = {
        c: f1_score(train["label"], cross_validate(train, c), average="macro")
        for c in C_VALUES
    }
    return max(scores, key=scores.get), scores


def compute_metrics(true_labels, predicted_labels):
    """Return the scores we report. "Caught" means spam or smishing not rated ham."""
    true_labels = list(true_labels)
    predicted_labels = list(predicted_labels)
    genuine = [p for t, p in zip(true_labels, predicted_labels) if t == "ham"]
    unwanted = [p for t, p in zip(true_labels, predicted_labels) if t != "ham"]
    report = classification_report(
        true_labels, predicted_labels, labels=LABELS, output_dict=True, zero_division=0
    )
    return {
        "scam_vs_safe_recall": sum(p != "ham" for p in unwanted) / len(unwanted),
        "false_alarm_rate": sum(p != "ham" for p in genuine) / len(genuine),
        "macro_f1": f1_score(true_labels, predicted_labels, labels=LABELS, average="macro"),
        "accuracy": accuracy_score(true_labels, predicted_labels),
        "per_class": {label: report[label] for label in LABELS},
        "confusion_matrix": {
            "labels": LABELS,
            "rows_true_columns_predicted": confusion_matrix(
                true_labels, predicted_labels, labels=LABELS
            ).tolist(),
        },
    }


def train_and_evaluate(data):
    """Run the full pipeline on a loaded dataset. Returns (model, metrics)."""
    prepared = prepare_data(data)
    train, test = split_data(prepared)

    best_c, c_scores = choose_c(train)
    model = build_model(best_c).fit(train["text"], train["label"])

    metrics = {
        "model_version": MODEL_VERSION,
        "scikit_learn_version": sklearn.__version__,
        "messages": {"total": len(prepared), "train": len(train), "test": len(test)},
        "c": best_c,
        "cross_validation_macro_f1_by_c": {str(c): score for c, score in c_scores.items()},
        "cross_validation": compute_metrics(train["label"], cross_validate(train, best_c)),
        "test": compute_metrics(test["label"], model.predict(test["text"])),
    }
    return model, metrics


def save_model(model, metrics, directory=MODELS_DIR):
    """Write the model, metrics and checksum files. Returns their paths."""
    directory = Path(directory)
    model_path = directory / f"model_{MODEL_VERSION}.joblib"
    metrics_path = directory / f"model_{MODEL_VERSION}_metrics.json"
    checksum_path = directory / f"model_{MODEL_VERSION}.sha256"
    joblib.dump(model, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    checksum_path.write_text(hashlib.sha256(model_path.read_bytes()).hexdigest(), encoding="utf-8")
    return model_path, metrics_path, checksum_path


def main():
    model, metrics = train_and_evaluate(load_dataset())
    save_model(model, metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
