"""Stage 11 tests: the reference set and its evaluation script."""
from collections import Counter

import pytest

from app.check_service import CheckService
from app.classifier import MockClassifier, Prediction
from app.preprocessor import clean_text
from training.data import load_dataset
from training.evaluate_reference import (
    LABELS,
    ORIGINS,
    evaluate,
    load_reference_set,
    main,
    outcome,
    split_halves,
    summarise,
)
from training.train import prepare_data


@pytest.fixture(scope="module")
def rows():
    return load_reference_set()


def test_every_row_is_valid(rows):
    assert len(rows) >= 40
    for row in rows:
        assert row["text"].strip(), row["id"]
        assert row["expected"] in LABELS, row["id"]
        assert row["origin"] in ORIGINS, row["id"]
        assert row["source"].strip(), row["id"]


def test_ids_are_unique(rows):
    assert len({row["id"] for row in rows}) == len(rows)


def test_scams_come_from_warnings_and_others_are_made_up(rows):
    for row in rows:
        if row["origin"] in ("verbatim", "modelled"):
            assert row["expected"] == "smishing" and row["source"].startswith("https://"), row["id"]
        else:
            assert row["source"] == "made up", row["id"]


def test_no_duplicate_messages_after_cleaning(rows):
    cleaned = [clean_text(row["text"]).strip() for row in rows]
    assert len(set(cleaned)) == len(cleaned)


def test_no_message_is_in_the_training_data(rows):
    training_texts = set(prepare_data(load_dataset())["text"].str.strip())
    overlap = [row["id"] for row in rows if clean_text(row["text"]).strip() in training_texts]
    assert overlap == []


def test_each_class_and_origin_is_split_evenly(rows):
    halves = split_halves(rows)
    groups = Counter()
    for row in rows:
        groups[(row["expected"], row["origin"], halves[row["id"]])] += 1
    for expected, origin in {(r["expected"], r["origin"]) for r in rows}:
        design, held_out = groups[(expected, origin, "design")], groups[(expected, origin, "held_out")]
        assert abs(design - held_out) <= 1, (expected, origin)


def test_split_is_repeatable_and_ignores_row_order(rows):
    assert split_halves(rows) == split_halves(list(reversed(rows)))


@pytest.mark.parametrize("expected, label, result", [
    ("smishing", "smishing", "caught"),
    ("smishing", "spam", "caught"),
    ("smishing", "unsure", "unsure"),
    ("smishing", "ham", "missed"),
    ("spam", "ham", "missed"),
    ("ham", "ham", "correct"),
    ("ham", "unsure", "unsure"),
    ("ham", "spam", "false alarm"),
    ("ham", "smishing", "false alarm"),
])
def test_outcome(expected, label, result):
    assert outcome(expected, label) == result


def test_summary_counts_on_a_made_up_set():
    legit = Prediction("ham", {"ham": 0.9, "spam": 0.05, "smishing": 0.05}, 3)
    service = CheckService(MockClassifier(legit))
    made_up = [
        {"id": "a", "text": "one", "expected": "smishing", "origin": "modelled"},
        {"id": "b", "text": "two", "expected": "smishing", "origin": "modelled"},
        {"id": "c", "text": "three", "expected": "ham", "origin": "made_up"},
    ]
    counts = summarise(evaluate(made_up, service))
    assert counts == Counter({("smishing", "modelled", "missed"): 2, ("ham", "made_up", "correct"): 1})


def test_script_scores_only_the_design_half_by_default(rows, capsys):
    halves = split_halves(rows)
    results = main([], service=CheckService(MockClassifier()))
    assert {r["id"] for r in results} == {id_ for id_, half in halves.items() if half == "design"}


def test_held_out_half_needs_the_flag(rows, capsys):
    halves = split_halves(rows)
    results = main(["--held-out"], service=CheckService(MockClassifier()))
    assert {r["id"] for r in results} == {id_ for id_, half in halves.items() if half == "held_out"}
