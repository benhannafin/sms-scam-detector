"""Stage 3 tests: training, evaluating and saving the model."""
import json

import joblib
import pandas as pd
import pytest

from training.data import load_dataset
from training.train import (
    C_VALUES,
    choose_c,
    compute_metrics,
    cross_validate,
    prepare_data,
    save_model,
    split_data,
    train_and_evaluate,
)

TEMPLATES = {
    "ham": "see you at lunch later today friend number{}",
    "spam": "free ringtone club offer text now tune{}",
    "smishing": "urgent your account is locked verify now case{}",
}


@pytest.fixture
def made_up_data():
    rows = [
        (label, template.format(i))
        for label, template in TEMPLATES.items()
        for i in range(40)
    ]
    return pd.DataFrame(rows, columns=["label", "text"])


def test_prepare_data_cleans_the_text():
    data = pd.DataFrame({"label": ["spam"], "text": ["WIN £500 NOW"]})
    assert prepare_data(data)["text"].tolist() == ["win moneytoken now"]


def test_prepare_data_removes_repeats_created_by_cleaning():
    data = pd.DataFrame({
        "label": ["smishing", "smishing"],
        "text": ["Call 08000930705 now", "Call 08000839402 now"],
    })
    assert prepare_data(data)["text"].tolist() == ["call phonetoken now"]


def test_prepare_data_removes_conflicts_created_by_cleaning():
    data = pd.DataFrame({
        "label": ["spam", "smishing", "ham"],
        "text": ["Win £5 now", "Win £10 now", "See you soon"],
    })
    assert prepare_data(data)["text"].tolist() == ["see you soon"]


def test_split_is_repeatable(made_up_data):
    first_train, first_test = split_data(made_up_data)
    second_train, second_test = split_data(made_up_data)
    assert first_train["text"].tolist() == second_train["text"].tolist()
    assert first_test["text"].tolist() == second_test["text"].tolist()


def test_split_is_80_20_and_keeps_the_class_mix(made_up_data):
    train, test = split_data(made_up_data)
    assert (len(train), len(test)) == (96, 24)
    assert test["label"].value_counts().to_dict() == {"ham": 8, "spam": 8, "smishing": 8}


def test_no_message_is_in_both_sets(made_up_data):
    train, test = split_data(made_up_data)
    assert set(train["text"]).isdisjoint(test["text"])


def test_metrics_on_a_worked_example():
    true = ["ham", "ham", "ham", "ham", "spam", "spam", "smishing", "smishing"]
    predicted = ["ham", "ham", "ham", "spam", "spam", "ham", "spam", "smishing"]
    metrics = compute_metrics(true, predicted)

    assert metrics["scam_vs_safe_recall"] == 3 / 4
    assert metrics["false_alarm_rate"] == 1 / 4
    assert metrics["accuracy"] == 5 / 8
    assert metrics["per_class"]["smishing"]["recall"] == 1 / 2
    assert metrics["confusion_matrix"]["rows_true_columns_predicted"] == [
        [3, 1, 0],
        [1, 1, 0],
        [0, 1, 1],
    ]


def test_choose_c_returns_the_best_of_the_values_tried(made_up_data):
    train, _ = split_data(made_up_data)
    best, scores = choose_c(train)
    assert list(scores) == C_VALUES
    assert scores[best] == max(scores.values())


def test_saved_model_loads_and_gives_the_same_probabilities(made_up_data, tmp_path):
    model, metrics = train_and_evaluate(made_up_data)
    model_path, _ = save_model(model, metrics, tmp_path)

    message = ["your account is locked"]
    loaded = joblib.load(model_path)
    assert loaded.predict_proba(message).tolist() == model.predict_proba(message).tolist()


def test_metrics_file_contains_no_message_text(made_up_data, tmp_path):
    model, metrics = train_and_evaluate(made_up_data)
    _, metrics_path = save_model(model, metrics, tmp_path)

    saved = metrics_path.read_text(encoding="utf-8")
    assert json.loads(saved)["model_version"] == "v1"
    for message in made_up_data["text"]:
        assert message not in saved


def test_real_data_meets_the_floor_in_cross_validation():
    # Only the training portion is used, so this never touches the test set.
    train, _ = split_data(prepare_data(load_dataset()))
    metrics = compute_metrics(train["label"], cross_validate(train, c=1))
    assert metrics["scam_vs_safe_recall"] >= 0.92
    assert metrics["false_alarm_rate"] <= 0.05
