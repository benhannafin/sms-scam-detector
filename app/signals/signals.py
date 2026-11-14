"""Hand-written warning signs (decision 041). The app assumes the sender is unknown.

Patterns run on cleaned text: lowercase, with money amounts as "moneytoken".
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Sign:
    name: str
    term: str  # the matched words, for highlighting
    text: str  # the reason shown to the user


_NUMBER = r"(?:moneytoken|money|cash|\d+)"

PATTERNS = [
    ("new_number", "Says it's from a new or temporary number", [
        r"\b(?:new|temporary|temp|other|different) (?:phone )?number\b",
        r"\bsave (?:this|my) (?:new )?number\b",
        r"\bphone (?:is |has )?(?:broken|broke|crashed|dead|lost|not working|stopped working)\b",
        r"\b(?:dropped|broke|lost|smashed) my phone\b",
    ]),
    ("card_or_code", "Asks for card details or a code", [
        r"\b(?:photo|picture|pic) of (?:your|ur|the) (?:bank )?card\b",
        r"\bcard (?:number|details)\b",
        # Asking for a code, not giving one: "your code is 482913" doesn't match.
        r"\b(?:send|give|tell|reply with|text) (?:me |us )?(?:the |your |that )?(?:\d+-digit )?code\b",
    ]),
    ("money_request", "Asks you to send money or pay something", [
        rf"\bsend (?:me|us) (?:some )?{_NUMBER}",
        rf"\btransfer (?:me |us )?(?:some )?{_NUMBER}",
        r"\bpay (?:a|the|my|this) (?:bill|invoice|fee) for (?:me|us)\b",
        r"\blend (?:me|us)\b",
        r"\bneeds? (?:some )?money\b",
    ]),
]

COMPILED = [(name, text, [re.compile(p) for p in patterns]) for name, text, patterns in PATTERNS]


def find_signs(cleaned_text):
    """Return the warning signs in a cleaned message, at most one of each kind."""
    signs = []
    for name, text, patterns in COMPILED:
        for pattern in patterns:
            match = pattern.search(cleaned_text)
            if match:
                signs.append(Sign(name=name, term=match.group(0), text=text))
                break
    return signs
