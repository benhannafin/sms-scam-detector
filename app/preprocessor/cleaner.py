"""Clean message text for the model (rules in decision 030)."""
import re

HTML_PLACEHOLDER = re.compile(r"&lt;[^&\s]*&gt;|&lt;|&gt;")

_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_CURRENCY_CODE = r"rs|inr|usd|gbp|eur"

# The lookarounds stop these matching inside an email address.
URL = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|(?<![@\w.-])[a-z0-9-]+(?:\.[a-z0-9-]+)*"
    r"\.(?:com|net|org|co\.uk|org\.uk|uk|ie|info|biz|tv|ly)\b(?![@\w-])(?:/\S*)?"
)

MONEY = re.compile(
    rf"[£$€₹]\s?{_NUMBER}(?:k|m|bn)?\b"
    rf"|\b(?:{_CURRENCY_CODE})\.?\s?{_NUMBER}"
    rf"|\b{_NUMBER}\s?(?:pounds?|dollars?|euros?|rupees?|lakhs?|crores?|{_CURRENCY_CODE})\b"
    r"|\b\d+(?:\.\d+)?(?:p|\s?ppm)\b"
)

PHONE = re.compile(r"(?<![\w.])\+?\d(?:[ -]?\d){6,}(?![\w@])")


def clean_text(text):
    """Return text lowercased, with HTML-style codes removed and tokens swapped in."""
    # Order matters: a link can contain digits, and a large amount looks like a phone number.
    cleaned = text.lower()
    cleaned = cleaned.replace("&amp;", "&")
    cleaned = HTML_PLACEHOLDER.sub("", cleaned)
    cleaned = URL.sub("urltoken", cleaned)
    cleaned = MONEY.sub("moneytoken", cleaned)
    cleaned = PHONE.sub("phonetoken", cleaned)
    return cleaned
