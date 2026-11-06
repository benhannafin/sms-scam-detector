"""The Flask app factory (decision 035)."""
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.api import RATE_LIMIT, api, error_response
from app.check_service import CheckService
from app.classifier import ModelLoadError, load_model

MODEL_VERSION = "v1"
MAX_REQUEST_BYTES = 16 * 1024


def create_app(classifier=None):
    """Create the app. With no classifier given, load the saved model once."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    if classifier is None:
        try:
            classifier = load_model(MODEL_VERSION)
        except ModelLoadError as error:
            # The app still starts, so the site can say the checker is unavailable.
            app.logger.error("Model failed to load: %s", error)
    app.extensions["check_service"] = CheckService(classifier) if classifier else None

    # A new limiter per app, so each app (and each test) counts from zero.
    limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
    limiter.limit(RATE_LIMIT)(api)
    app.register_blueprint(api)

    @app.errorhandler(413)
    def request_too_large(error):
        return error_response(413, "request_too_large", "The request is too large.")

    @app.errorhandler(429)
    def rate_limited(error):
        return error_response(429, "rate_limited", "Too many checks. Please wait and try again later.")

    @app.errorhandler(500)
    def internal_error(error):
        return error_response(500, "internal_error", "Something went wrong. Please try again.")

    return app
