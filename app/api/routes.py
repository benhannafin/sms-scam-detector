"""POST /api/check: validate input and return a check result (decision 035)."""
from flask import Blueprint, current_app, jsonify, request

MAX_MESSAGE_LENGTH = 1000
RATE_LIMIT = "20 per hour"

api = Blueprint("api", __name__, url_prefix="/api")


def error_response(status, code, message):
    """The shape of every error. Never put the user's text in `message`."""
    return jsonify(error={"code": code, "message": message}), status


@api.post("/check")
def check():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("message"), str):
        return error_response(400, "invalid_request", 'Send JSON like {"message": "the text to check"}.')

    message = body["message"]
    if not message.strip():
        return error_response(400, "empty_message", "The message is empty.")
    if len(message) > MAX_MESSAGE_LENGTH:
        return error_response(
            400, "too_long", f"The message is over {MAX_MESSAGE_LENGTH} characters."
        )

    service = current_app.extensions["check_service"]
    if service is None:
        return error_response(503, "model_unavailable", "The checker is unavailable right now.")

    try:
        result = service.check(message)
    except Exception as error:
        # Only the error's type is logged: its text could include the message.
        current_app.logger.error("Check failed: %s", type(error).__name__)
        return error_response(500, "internal_error", "Something went wrong. Please try again.")

    return jsonify(
        label=result.label,
        confidence=result.confidence,
        status=result.status,
        reasons=[{"term": reason.term, "text": reason.text} for reason in result.reasons],
    )
