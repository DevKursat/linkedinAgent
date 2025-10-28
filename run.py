"""Application entry point."""
from src.app import app
from src.scheduler import start_scheduler
from src.db import init_db

# Initialize the database
init_db()

# Start the background scheduler
start_scheduler()

if __name__ == '__main__':
    # Running the app with Gunicorn is recommended for production.
    # Example: gunicorn --bind 0.0.0.0:5000 run:app
    # For simplicity in this project, we can run Flask's built-in server,
    # but it's not suitable for production.
    # The `app.run` call is handled in `src/app.py` when run as a script.
    # When using a WSGI server, the `app` object is imported and used.
    # To run with Flask's server for development:
    # FLASK_APP=run.py flask run
    pass
