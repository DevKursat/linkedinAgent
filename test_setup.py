"""
Test script to verify basic functionality of the LinkedIn bot
Run this before deploying to ensure everything is configured correctly
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        import config
        import database
        import linkedin_api
        import content_generator
        import news_fetcher
        import scheduler
        import app
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    try:
        from config import (
            LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, GEMINI_API_KEY,
            DATABASE_PATH, PERSONA_NAME, NEWS_SOURCES
        )
        
        if not LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_ID == 'your_client_id_here':
            print("✗ LINKEDIN_CLIENT_ID not configured")
            return False
            
        if not LINKEDIN_CLIENT_SECRET or LINKEDIN_CLIENT_SECRET == 'your_client_secret_here':
            print("✗ LINKEDIN_CLIENT_SECRET not configured")
            return False
            
        if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_gemini_api_key_here':
            print("✗ GEMINI_API_KEY not configured")
            return False
        
        print(f"✓ Configuration loaded")
        print(f"  Database: {DATABASE_PATH}")
        print(f"  Persona: {PERSONA_NAME}")
        print(f"  News sources: {len(NEWS_SOURCES)}")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        from database import init_db, get_daily_stats
        
        # Initialize database
        init_db()
        print("✓ Database initialized")
        
        # Test basic query
        stats = get_daily_stats()
        print(f"✓ Database query successful")
        print(f"  Today's stats: {stats}")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_news_fetcher():
    """Test news fetching"""
    print("\nTesting news fetcher...")
    try:
        from news_fetcher import fetch_all_news, select_best_article
        
        articles = fetch_all_news()
        print(f"✓ Fetched {len(articles)} articles")
        
        if articles:
            best = select_best_article(articles)
            if best:
                print(f"✓ Selected article: {best['title'][:50]}...")
            else:
                print("⚠ No article selected (but fetch worked)")
        else:
            print("⚠ No articles found (feeds might be down)")
        
        return True
    except Exception as e:
        print(f"✗ News fetcher error: {e}")
        return False


def test_gemini():
    """Test Gemini API connection"""
    print("\nTesting Gemini API...")
    try:
        from content_generator import detect_language
        
        # Simple test
        lang = detect_language("Hello, how are you?")
        print(f"✓ Gemini API working (detected language: {lang})")
        return True
    except Exception as e:
        print(f"✗ Gemini API error: {e}")
        print("  Check your GEMINI_API_KEY")
        return False


def test_flask_app():
    """Test Flask app initialization"""
    print("\nTesting Flask app...")
    try:
        from app import app
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            if response.status_code == 200:
                print("✓ Flask app working")
                print(f"  Health check: {response.json}")
                return True
            else:
                print(f"✗ Health check failed with status {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Flask app error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("LinkedIn Bot - Configuration Test")
    print("=" * 60)
    
    results = {
        "Imports": test_imports(),
        "Configuration": test_config(),
        "Database": test_database(),
        "News Fetcher": test_news_fetcher(),
        "Gemini API": test_gemini(),
        "Flask App": test_flask_app(),
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print("=" * 60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Your bot is ready to run.")
        print("\nNext steps:")
        print("1. Authenticate with LinkedIn: python app.py then visit http://localhost:5000/login")
        print("2. Start the scheduler: python scheduler.py")
        return 0
    else:
        print("\n⚠ Some tests failed. Please fix the issues before running the bot.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
