"""Warning signs: what's in a message, and why it matters (decisions 041, 043).

The app assumes the sender is unknown. Patterns run on cleaned text: lowercase, with links,
phone numbers and money amounts as "urltoken", "phonetoken" and "moneytoken".
Only the first three signs can change a result; the rest are explanation only.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Sign:
    name: str
    term: str  # the matched words
    text: str  # the reason shown: "Title: why it matters"
    changes_result: bool


_NUMBER = r"(?:moneytoken|money|cash|\d+)"

# (name, title, why it matters, can change the result, patterns), in the order reasons are shown.
SIGNS = [
    ("new_number", "Says it's from a new or temporary number",
     "scammers often pretend to be family or friends who've lost their phone.", True, [
        r"\b(?:new|temporary|temp|other|different) (?:phone )?number\b",
        r"\bsave (?:this|my) (?:new )?number\b",
        r"\bphone (?:is |has )?(?:broken|broke|crashed|dead|lost|not working|stopped working)\b",
        r"\b(?:dropped|broke|lost|smashed) my phone\b",
    ]),
    ("card_or_code", "Asks for card details or a code",
     "a genuine bank or company won't ask for these by text.", True, [
        r"\b(?:photo|picture|pic) of (?:your|ur|the) (?:bank )?card\b",
        r"\bcard (?:number|details)\b",
        # Asking for a code, not giving one: "your code is 482913" doesn't match.
        r"\b(?:send|give|tell|reply with|text) (?:me |us )?(?:the |your |that )?(?:\d+-digit )?code\b",
    ]),
    ("money_request", "Asks you to send money",
     "don't send money to a number you don't know without checking first.", True, [
        rf"\bsend (?:me|us) (?:some )?{_NUMBER}",
        rf"\btransfer (?:me |us )?(?:some )?{_NUMBER}",
        r"\bpay (?:a|the|my|this) (?:bill|invoice|fee) for (?:me|us)\b",
        r"\blend (?:me|us)\b",
        r"\bneeds? (?:some )?money\b",
    ]),
    ("link", "Contains a link",
     "scam texts often lead to fake websites that look real.", False, [r"\burltoken\b"]),
    ("phone_number", "Contains a phone number",
     "scam texts often give a number that goes to the scammer, not the real company.", False,
     [r"\bphonetoken\b"]),
    ("prize", "Mentions winning or a prize",
     "offers that seem too good to be true are a common lure.", False, [
        r"\b(?:win|winner|winning|won|prize|prizes|claim|selected|congratulations|reward)\b",
    ]),
    ("account", "Mentions your account or security",
     "a common way to make a text feel official and urgent.", False, [
        r"\b(?:account|verify|verification|log ?in|password|suspended|restricted|locked|limited"
        r"|unauthori[sz]ed|device)\b",
    ]),
    ("payment", "Mentions a payment or fee",
     "texts asking you to pay something or claim a refund are a common scam.", False, [
        r"\b(?:fee|fees|pay|payment|unpaid|charge|charges|outstanding|refund|bill)\b",
    ]),
    ("urgency", "Creates urgency",
     "pressure to act quickly is a classic scam tactic.", False, [
        r"\b(?:urgent|urgently|immediately|asap|today|expire|expires|final notice|last chance)\b",
        r"\bwithin \d+ (?:hours|hrs|days)\b",
    ]),
    ("money_amount", "Mentions an amount of money",
     "small fees and big prizes both appear often in scam texts.", False, [r"\bmoneytoken\b"]),
    ("opt_out", "Has opt-out wording (STOP)",
     "this is typical of marketing texts.", False, [
        r"\b(?:txt|text|reply|send) stop\b",
        r"\bstop to\b",
        r"\bunsubscribe\b",
        r"\bopt[ -]?out\b",
    ]),
]

COMPILED = [
    (name, f"{title}: {why}", changes, [re.compile(p) for p in patterns])
    for name, title, why, changes, patterns in SIGNS
]


def find_signs(cleaned_text):
    """Return the warning signs in a cleaned message, at most one of each kind, in list order."""
    signs = []
    for name, text, changes, patterns in COMPILED:
        for pattern in patterns:
            match = pattern.search(cleaned_text)
            if match:
                signs.append(Sign(name=name, term=match.group(0), text=text, changes_result=changes))
                break
    return signs
