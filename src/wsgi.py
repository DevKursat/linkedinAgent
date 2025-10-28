"""WSGI entry point for gunicorn."""
from .main import app

application = app
