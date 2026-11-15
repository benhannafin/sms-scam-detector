"""The Flask app factory (decisions 035, 037, 044)."""
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from werkzeug.middleware.proxy_fix import ProxyFix

from app.api import RATE_LIMIT, api, error_response
from app.check_service import CheckService
from app.classifier import ModelLoadError, load_model
from app.web import web

MODEL_VERSION = "v1"
MAX_REQUEST_BYTES = 16 * 1024

# Standard browser protections on every response (decision 044). The policy allows only our own
# scripts and styles, plus Google Fonts; the page has no inline scripts or styles.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


def strip_port(address):
    """Remove a port: Azure passes "1.2.3.4:56789", and the port changes every connection."""
    if address.startswith("["):  # [IPv6]:port
        return address[1:].split("]")[0]
    if address.count(":") == 1:  # IPv4:port
        return address.split(":")[0]
    return address  # IPv4, or IPv6 without a port


def client_address():
    """The rate limit's key: one per user, not one per connection."""
    return strip_port(request.remote_addr or "")


def create_app(classifier=None):
    """Create the app. With no classifier given, load the saved model once."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
    # Trust the one address Azure's front end adds; anything a user adds before it is ignored.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    if classifier is None:
        try:
            classifier = load_model(MODEL_VERSION)
        except ModelLoadError as error:
            # The app still starts, so the site can say the checker is unavailable.
            app.logger.error("Model failed to load: %s", error)
    app.extensions["check_service"] = CheckService(classifier) if classifier else None

    # A new limiter per app, so each app (and each test) counts from zero.
    limiter = Limiter(client_address, app=app, storage_uri="memory://")
    limiter.limit(RATE_LIMIT)(api)
    app.register_blueprint(api)
    app.register_blueprint(web)

    @app.get("/health")
    def health():
        # Not rate limited, and no message data: for monitors, and for waking the site.
        if app.extensions["check_service"] is None:
            return jsonify(status="model_unavailable"), 503
        return jsonify(status="ok")

    @app.after_request
    def add_security_headers(response):
        response.headers.update(SECURITY_HEADERS)
        return response

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
