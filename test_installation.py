#!/usr/bin/env python3
"""Test script to verify LinkedIn Agent installation."""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all essential modules can be imported."""
    print("Testing imports...")
    try:
        from src import main
        from src import config
        from src import database
        from src import models
        from src import persona
        from src import scheduler
        from src import ai_core
        print("✓ All essential imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from src.config import settings
        # We only check if settings can be loaded
        print("✓ Configuration module loaded")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def test_database():
    """Test database initialization and model creation."""
    print("\nTesting database...")
    try:
        from src.database import engine, Base
        from src.models import Post, Comment, Invitation, ActionLog
        
        # This implicitly tests that models are defined correctly
        print("✓ Database and models are defined correctly")
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fastapi_app():
    """Test FastAPI application."""
    print("\nTesting FastAPI app...")
    try:
        from src.main import app
        
        if app is None:
            print("✗ FastAPI app not created")
            return False
        
        # Check routes by inspecting the app's routes attribute
        routes = {route.path for route in app.routes}
        required_api_routes = {
            '/', '/health',
            '/api/scheduled-jobs', '/api/trigger/post',
            '/api/trigger/comment', '/api/trigger/invite',
            '/login', '/callback'
        }
        
        # Check for the main API routes
        if not required_api_routes.issubset(routes):
            missing = required_api_routes - routes
            print(f"✗ Required API routes missing: {missing}")
            return False

        # Check for static route mount separately
        if not any(r.path.startswith('/static') for r in app.routes):
             print(f"✗ Required static route mount is missing")
             return False
        
        print("✓ FastAPI app configured correctly")
        return True
        
    except Exception as e:
        print(f"✗ FastAPI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("LinkedIn Agent - Installation Test (FastAPI Version)")
    print("="*60)
    
    tests = [
        test_imports,
        test_config,
        test_database,
        test_fastapi_app,
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
        print("1. Fill in your credentials in the .env file")
        print("2. Run the server with: uvicorn src.main:app --reload")
        print("3. Open http://127.0.0.1:8000 in your browser")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
