"""Turn a prediction into reasons people can read (decision 043, replacing 033's word reasons).

Reasons are the warning signs found in the message, each with why it matters. They no longer
come from the model's word weights, which were faithful but meaningless to a reader.
"""
from dataclasses import dataclass

from app.signals import find_signs

MAX_REASONS = 3


@dataclass(frozen=True)
class Reason:
    term: str | None
    text: str


NO_SIGNS = Reason(term=None, text="No common warning signs found")
# When no sign is found, say plainly that the model's learned wording made the call.
FALLBACKS = {
    "smishing": Reason(term=None, text="The wording is similar to scam texts the model learned from."),
    "spam": Reason(term=None, text="The wording is similar to marketing texts the model learned from."),
    "ham": NO_SIGNS,
}


def explain(cleaned_text, prediction):
    """Return up to 3 reasons for a prediction: warning signs first, or a fallback."""
    signs = find_signs(cleaned_text)
    if prediction.label == "spam":
        # The opt-out wording is the clearest marketing clue, so it leads.
        signs = sorted(signs, key=lambda sign: sign.name != "opt_out")
    reasons = [Reason(term=sign.term, text=sign.text) for sign in signs][:MAX_REASONS]
    return reasons or [FALLBACKS[prediction.label]]
