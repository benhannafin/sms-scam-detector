"""Turn a prediction into reasons people can read (rules in decision 033)."""
from dataclasses import dataclass
import re

MAX_REASONS = 3
# Weaker terms are mostly filler words like "the"; chosen by eye, to revisit in Stage 10.
MIN_STRENGTH = 0.15

TOKEN_TEXT = {
    "urltoken": "Contains a link",
    "moneytoken": "Mentions an amount of money",
    "phonetoken": "Contains a phone number",
}
TOKEN_NAME = {
    "urltoken": "[link]",
    "moneytoken": "[amount of money]",
    "phonetoken": "[phone number]",
}

# Matches how the model splits text into words, so terms can be checked against the message.
WORD = re.compile(r"(?u)\b\w\w+\b")


@dataclass(frozen=True)
class Reason:
    term: str | None
    text: str


NO_SIGNS = Reason(term=None, text="No common scam signs found")


def explain(cleaned_text, prediction):
    """Return up to 3 reasons for a prediction, biggest first."""
    if prediction.label == "ham":
        # Only terms that pointed away from ham: never cite evidence that a message is genuine.
        scores = {term: -c["ham"] for term, c in prediction.contributions.items()}
    else:
        scores = {term: c[prediction.label] for term, c in prediction.contributions.items()}

    in_message = _terms_in(cleaned_text)
    candidates = sorted(
        (term for term, score in scores.items() if score >= MIN_STRENGTH and term in in_message),
        key=lambda term: (-scores[term], term),
    )

    chosen = []
    for term in candidates:
        if len(chosen) == MAX_REASONS:
            break
        if not any(set(term.split()) & set(other.split()) for other in chosen):
            chosen.append(term)

    if not chosen and prediction.label == "ham":
        return [NO_SIGNS]
    return [Reason(term=term, text=_describe(term)) for term in chosen]


def _terms_in(cleaned_text):
    words = WORD.findall(cleaned_text)
    return set(words) | {f"{a} {b}" for a, b in zip(words, words[1:])}


def _describe(term):
    if term in TOKEN_TEXT:
        return TOKEN_TEXT[term]
    words = term.split()
    if len(words) == 1:
        return f'Uses the word "{term}"'
    return 'Uses the phrase "{}"'.format(" ".join(TOKEN_NAME.get(word, word) for word in words))
