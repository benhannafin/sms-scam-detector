"""The web pages (decision 036)."""
from flask import Blueprint, render_template

from app.api import MAX_MESSAGE_LENGTH

# "/assets" avoids clashing with Flask's own "/static" route.
web = Blueprint(
    "web", __name__, template_folder="templates", static_folder="static", static_url_path="/assets"
)

# Made-up messages, worded so each chip shows a different result with model v1.
EXAMPLES = [
    {
        "name": "Parcel fee",
        "message": "Your package is waiting. To arrange delivery, call 0871 234 5678 now and pay the 1.50 fee to claim it.",
        "expected_label": "smishing",
    },
    {
        "name": "Prize offer",
        "message": "WIN a weekend for two in our summer draw! Txt WIN to 80888 to enter. Free entry, std txt rate. Txt STOP to end.",
        "expected_label": "spam",
    },
    {
        "name": "Friend running late",
        "message": "Running about ten minutes late, sorry! Save me a seat and I'll see you soon.",
        "expected_label": "ham",
    },
]


@web.get("/")
def home():
    return render_template("index.html", max_length=MAX_MESSAGE_LENGTH, examples=EXAMPLES)
