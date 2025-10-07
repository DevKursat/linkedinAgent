#!/usr/bin/env python3
"""Test script to verify LinkedIn Agent installation."""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from src import config
        from src import db
        from src import linkedin_api
        from src import gemini
        from src import sources
        from src import moderation
        from src import generator
        from src import utils
        from src import commenter
        from src import proactive
        from src import scheduler
        from src import main
        from src import worker
        from src import wsgi
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from src.config import config
        print(f"  DRY_RUN: {config.DRY_RUN}")
        print(f"  Persona: {config.PERSONA_NAME}, {config.PERSONA_AGE}, {config.PERSONA_ROLE}")
        print(f"  Timezone: {config.TZ}")
        print("✓ Configuration loaded")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False


def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    try:
        import os
        import tempfile
        
        # Use temporary database
        test_db = os.path.join(tempfile.gettempdir(), 'test_linkedin_agent.db')
        os.environ['DB_PATH'] = test_db
        
        from src import config
        config.config.DB_PATH = test_db
        
        from src.db import init_db, save_post, get_recent_posts
        
        init_db()
        
        # Test CRUD operations
        save_post('test123', 'urn:test', 'Test post content', 'https://example.com')
        posts = get_recent_posts(limit=1)
        
        if len(posts) == 1 and posts[0]['content'] == 'Test post content':
            print("✓ Database operations working")
            
            # Cleanup
            if os.path.exists(test_db):
                os.remove(test_db)
            return True
        else:
            print("✗ Database test failed: unexpected data")
            return False
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_moderation():
    """Test content moderation."""
    print("\nTesting moderation...")
    try:
        from src.moderation import should_post_content, is_blocked
        
        # Test blocking
        blocked, reason = is_blocked("This election is important")
        if not blocked:
            print("✗ Politics should be blocked")
            return False
        
        blocked, reason = is_blocked("Bitcoin to the moon")
        if not blocked:
            print("✗ Crypto should be blocked")
            return False
        
        # Test normal content
        should_post, reason = should_post_content("AI is transforming product development")
        if not should_post:
            print(f"✗ Normal content should pass: {reason}")
            return False
        
        print("✓ Moderation working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Moderation test failed: {e}")
        return False


def test_utils():
    """Test utility functions."""
    print("\nTesting utilities...")
    try:
        from src.utils import get_istanbul_time, detect_language, is_negative_sentiment
        
        # Test timezone
        ist_time = get_istanbul_time()
        if ist_time is None:
            print("✗ Failed to get Istanbul time")
            return False
        
        # Test language detection
        lang = detect_language("Hello world")
        if lang not in ['en', 'nl']:  # langdetect can vary
            print(f"✗ Unexpected language detection: {lang}")
        
        # Test sentiment
        if not is_negative_sentiment("This is terrible"):
            print("✗ Sentiment detection failed")
            return False
        
        print("✓ Utilities working")
        return True
        
    except Exception as e:
        print(f"✗ Utils test failed: {e}")
        return False


def test_flask_app():
    """Test Flask application."""
    print("\nTesting Flask app...")
    try:
        import os
        import tempfile
        
        test_db = os.path.join(tempfile.gettempdir(), 'test_flask.db')
        os.environ['DB_PATH'] = test_db
        
        from src.main import app
        from src.db import init_db
        
        init_db()
        
        # Check app exists
        if app is None:
            print("✗ Flask app not created")
            return False
        
        # Check routes
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        required_routes = ['/', '/health', '/login', '/callback', '/queue']
        
        for route in required_routes:
            if route not in routes:
                print(f"✗ Required route missing: {route}")
                return False
        
        print("✓ Flask app configured correctly")
        
        # Cleanup
        if os.path.exists(test_db):
            os.remove(test_db)
        
        return True
        
    except Exception as e:
        print(f"✗ Flask test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("LinkedIn Agent - Installation Test")
    print("="*60)
    
    tests = [
        test_imports,
        test_config,
        test_database,
        test_moderation,
        test_utils,
        test_flask_app,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)
    
    if all(results):
        print("\n✓ All tests passed! LinkedIn Agent is ready.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and fill in your credentials")
        print("2. Run: docker compose up -d --build")
        print("3. Open http://localhost:5000")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
