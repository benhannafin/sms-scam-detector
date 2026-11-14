"""Stage 11 tests: hand-written warning signs (decision 041)."""
import pytest

from app.preprocessor import clean_text
from app.signals import Sign, find_signs


def names(message):
    return [sign.name for sign in find_signs(clean_text(message))]


@pytest.mark.parametrize("message", [
    "Hi mum, this is my new number",
    "Hi Dad it's me, this is my temporary number",
    "hey mam, my phone is not working , save this number and use on Whatsapp",
    "My other phone crashed so text me here",
    "I dropped my phone in the sink",
    "My phone is broken, use this one",
])
def test_new_number_openers(message):
    assert "new_number" in names(message)


@pytest.mark.parametrize("message", [
    "Can you send me a photo of your bank card",
    "Please confirm your card details",
    "Reply with the 6-digit code we just sent you",
    "Can you send me the code that just came through",
])
def test_asks_for_card_details_or_a_code(message):
    assert "card_or_code" in names(message)


@pytest.mark.parametrize("message", [
    "Can you send me 450 for my rent today?",
    "Can you send me €200 please",
    "Mam can you transfer me 20 for the bus",
    "could you pay a bill for me? I'll send you the details",
    "Can you lend me a few quid",
    "I need money urgently",
])
def test_asks_for_money(message):
    assert "money_request" in names(message)


@pytest.mark.parametrize("message", [
    "Your verification code is 482913. Do not share this code with anyone.",
    "Use code 719204 to sign in to your account.",
    "Can you send me the photos from the weekend when you get a chance?",
    "Your new SIM has been activated. Your number will move over within the next hour.",
    "Hi Dad, I'm at the shop, I have money so no need to send any",
    "Your electricity bill for October is EUR 86.40 and will be taken by direct debit.",
    "Running 10 mins late, traffic is mad. Order me a coffee?",
    "",
])
def test_genuine_texts_have_no_signs(message):
    assert names(message) == []


def test_at_most_one_sign_of_each_kind_in_a_fixed_order():
    message = "Hi mum new number, my phone is broken. Send me 50 and a photo of your card, transfer me 20"
    assert names(message) == ["new_number", "card_or_code", "money_request"]


def test_sign_records_the_matched_words_and_the_reason():
    assert find_signs(clean_text("Hi mum, this is my new number")) == [
        Sign(name="new_number", term="new number", text="Says it's from a new or temporary number")
    ]


def test_reason_wording_never_says_safe():
    from app.signals.signals import PATTERNS
    assert all("safe" not in text.lower() for _, text, _ in PATTERNS)
