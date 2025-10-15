import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.run_dev_server import app  # note: run_dev_server imports src.main

# If imported this way, re-import actual app
from src.main import app as flask_app

if __name__ == '__main__':
    print('Starting dev server on http://0.0.0.0:5001')
    flask_app.run(host='0.0.0.0', port=5001, debug=True)
