"""Stage 2 tests: cleaning message text."""
import pytest

from app.preprocessor import clean_text


def test_text_is_lowercased():
    assert clean_text("Call ME Now") == "call me now"


def test_ampersand_code_becomes_an_ampersand():
    assert clean_text("fish &amp; chips") == "fish & chips"


@pytest.mark.parametrize("code", ["&lt;#&gt;", "&lt;DECIMAL&gt;", "&lt;TIME&gt;", "&lt;", "&gt;"])
def test_html_placeholders_are_removed(code):
    assert clean_text(f"see you at {code}") == "see you at "


@pytest.mark.parametrize("link", [
    "http://www.urawinner.com",
    "https://example.ie/claim?id=1",
    "www.getzed.co.uk",
    "notxt.co.uk",
    "tlp.co.uk/expressoffer",
    "100percent-real.com",
    "bit.ly/abc123",
    "an-post.ie",
])
def test_links_become_urltoken(link):
    assert clean_text(f"go to {link} today") == "go to urltoken today"


@pytest.mark.parametrize("amount", [
    "£200",
    "£1.50",
    "£2,000",
    "£5k",
    "$50",
    "€100",
    "₹500",
    "rs.2,00,000",
    "rs650",
    "inr 5,00,000",
    "3gbp",
    "500 pounds",
    "750 pound",
    "20 euro",
    "2 lakhs",
    "150p",
    "1.50p",
    "150ppm",
    "150 ppm",
])
def test_money_becomes_moneytoken(amount):
    assert clean_text(f"win {amount} today") == "win moneytoken today"


@pytest.mark.parametrize("number", [
    "1234567",
    "08000930705",
    "0800 542 0578",
    "087-123-4567",
    "+353 87 123 4567",
])
def test_phone_numbers_become_phonetoken(number):
    assert clean_text(f"call {number} today") == "call phonetoken today"


def test_digits_in_a_link_are_not_a_phone_number():
    assert clean_text("www.07781482378.com") == "urltoken"


def test_large_amount_is_money_not_a_phone_number():
    assert clean_text("£1000000") == "moneytoken"


@pytest.mark.parametrize("email", [
    "robertdep34@gmail.com",
    "john.me@yahoo.com",
    "info@txt82228.co.uk",
    "12345678@gmail.com",
])
def test_email_addresses_are_left_unchanged(email):
    assert clean_text(f"write to {email} today") == f"write to {email} today"


@pytest.mark.parametrize("text", [
    "text win to 86688",
    "your code is 123456",
    "see you at 8pm",
    "back in 2003",
])
def test_short_numbers_are_left_unchanged(text):
    assert clean_text(text) == text


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_text_does_not_crash(text):
    assert clean_text(text).strip() == ""


def test_several_tokens_in_one_message():
    message = "WIN £500! Call 08000930705 or visit www.prize.com"
    assert clean_text(message) == "win moneytoken! call phonetoken or visit urltoken"
