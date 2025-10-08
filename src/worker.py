"""Background worker that runs the scheduler."""
import time
from . import db
from .gemini import init_gemini
from .scheduler import start_scheduler


def main():
    """Main worker function."""
    print("Starting LinkedIn Agent Worker...")
    
    # Initialize database
    db.init_db()
    
    # Initialize Gemini
    init_gemini()
    
    # Start scheduler
    start_scheduler()
    
    # Keep alive
    print("Worker running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down worker...")


if __name__ == '__main__':
    main()
