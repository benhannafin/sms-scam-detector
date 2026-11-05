"""Load the SMS dataset and clean it for training (rules in decision 029)."""
from pathlib import Path

import pandas as pd

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "sms_phishing_dataset.csv"
LABELS = {"ham", "spam", "smishing"}


def load_dataset(path=DATASET_PATH):
    """Return the cleaned dataset as a DataFrame with columns `label` and `text`."""
    raw = pd.read_csv(path, encoding="utf-8", usecols=["LABEL", "TEXT"])
    data = pd.DataFrame({
        "label": raw["LABEL"].str.strip().str.lower(),
        "text": raw["TEXT"].str.strip(),
    })

    unknown = data.loc[~data["label"].isin(LABELS), "label"].unique().tolist()
    if unknown:
        raise ValueError(f"Unrecognised labels in dataset: {unknown}")

    return remove_conflicts_and_duplicates(data)


def remove_conflicts_and_duplicates(data):
    """Remove every copy of a message with conflicting labels, then repeated rows."""
    # Conflicts must go first: dropping duplicates can't tell which label is right.
    labels_per_text = data.groupby("text")["label"].transform("nunique")
    data = data[labels_per_text == 1]

    return data.drop_duplicates().reset_index(drop=True)
