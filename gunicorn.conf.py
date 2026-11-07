"""Gunicorn settings for Azure App Service (decision 037). Azure starts it with: gunicorn"""

wsgi_app = "app:create_app()"
bind = "0.0.0.0:8000"

# One process: the rate limiter counts in memory, so each extra process would allow
# another 20 checks an hour. Threads let it handle a few requests at once.
workers = 1
threads = 4

# Loading the model on a cold start can be slow on the free tier.
timeout = 120

# No access log: it would record every visitor's IP address, which isn't needed.
accesslog = None
