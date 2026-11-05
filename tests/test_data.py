"""Stage 1 tests: loading and cleaning the dataset."""
import pandas as pd
import pytest

from training.data import load_dataset


def write_csv(tmp_path, rows):
    """Write (LABEL, TEXT) rows to a temporary CSV with the real file's columns."""
    path = tmp_path / "messages.csv"
    frame = pd.DataFrame(rows, columns=["LABEL", "TEXT"])
    frame["URL"] = "No"
    frame["EMAIL"] = "No"
    frame["PHONE"] = "No"
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def test_pound_sign_is_read_correctly(tmp_path):
    data = load_dataset(write_csv(tmp_path, [("spam", "Win £200 now")]))
    assert data["text"].tolist() == ["Win £200 now"]


def test_only_label_and_text_are_returned(tmp_path):
    data = load_dataset(write_csv(tmp_path, [("ham", "See you soon")]))
    assert list(data.columns) == ["label", "text"]


def test_whitespace_is_trimmed(tmp_path):
    data = load_dataset(write_csv(tmp_path, [(" ham ", "\tSee you soon  ")]))
    assert data.to_dict("records") == [{"label": "ham", "text": "See you soon"}]


def test_label_spelling_is_normalised(tmp_path):
    rows = [("Spam", "Message one"), ("Smishing", "Message two"), ("ham", "Message three")]
    data = load_dataset(write_csv(tmp_path, rows))
    assert data["label"].tolist() == ["spam", "smishing", "ham"]


def test_duplicates_become_one_row(tmp_path):
    rows = [("ham", "See you soon"), ("ham", "See you soon")]
    data = load_dataset(write_csv(tmp_path, rows))
    assert data["text"].tolist() == ["See you soon"]


def test_duplicates_differing_by_a_leading_tab_become_one_row(tmp_path):
    rows = [("spam", "Win a prize"), ("spam", "\tWin a prize")]
    data = load_dataset(write_csv(tmp_path, rows))
    assert data["text"].tolist() == ["Win a prize"]


def test_conflicting_messages_are_removed_completely(tmp_path):
    rows = [("spam", "Win a prize"), ("smishing", "Win a prize"), ("ham", "See you soon")]
    data = load_dataset(write_csv(tmp_path, rows))
    assert data["text"].tolist() == ["See you soon"]


def test_conflicts_hidden_by_a_leading_tab_are_removed_completely(tmp_path):
    rows = [("spam", "Win a prize"), ("smishing", "\tWin a prize"), ("ham", "See you soon")]
    data = load_dataset(write_csv(tmp_path, rows))
    assert data["text"].tolist() == ["See you soon"]


def test_conflicting_message_with_repeated_label_is_removed_completely(tmp_path):
    rows = [("spam", "Win a prize"), ("spam", "Win a prize"), ("smishing", "Win a prize")]
    data = load_dataset(write_csv(tmp_path, rows))
    assert data.empty


def test_unrecognised_label_raises_a_clear_error(tmp_path):
    path = write_csv(tmp_path, [("smishng", "Win a prize")])
    with pytest.raises(ValueError, match="smishng"):
        load_dataset(path)


def test_real_dataset_gives_expected_counts():
    data = load_dataset()
    assert len(data) == 5797
    assert data["label"].value_counts().to_dict() == {"ham": 4834, "smishing": 528, "spam": 435}
