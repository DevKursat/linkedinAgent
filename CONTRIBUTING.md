# Contributing to LinkedIn Agent

Thank you for your interest in contributing to LinkedIn Agent! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and professional
- Test thoroughly before submitting PRs
- Write clear, concise commit messages
- Document your changes

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/linkedinAgent.git
   cd linkedinAgent
   ```
3. Set up development environment:
   ```bash
   cp .env.example .env
   # Fill in test credentials
   pip install -r requirements.txt
   ```

## Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Keep changes focused and minimal
- Follow existing code style
- Add comments for complex logic
- Update documentation if needed

### 3. Test Your Changes

**Required before submitting PR:**

```bash
# Run installation tests
python3 test_installation.py

# Test in DRY_RUN mode
python3 -c "
import os
os.environ['DRY_RUN'] = 'true'
from src.scheduler import run_daily_post
run_daily_post()
"

# Test specific module
python3 -c "
from src.moderation import should_post_content
assert should_post_content('AI is great')[0] == True
assert should_post_content('Election news')[0] == False
print('Tests passed!')
"
```

### 4. Commit Changes
```bash
git add .
git commit -m "Brief description of changes"
```

**Commit Message Guidelines:**
- Use present tense ("Add feature" not "Added feature")
- Be specific and concise
- Reference issues if applicable: "Fix #123: Description"

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python
- Follow PEP 8 style guide
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings for functions and classes

Example:
```python
def get_user_posts(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent posts for a user.
    
    Args:
        user_id: LinkedIn user ID
        limit: Maximum number of posts to return
        
    Returns:
        List of post dictionaries
    """
    # Implementation
    pass
```

### Modules
- One module per file
- Clear separation of concerns
- Import only what you need
- Avoid circular dependencies

## Testing

### Required Tests
1. **Installation test must pass**: `python3 test_installation.py`
2. **DRY_RUN mode must work**: Test your changes with DRY_RUN=true
3. **No breaking changes**: Existing functionality must continue working

### Writing Tests
Add tests to `test_installation.py` or create new test files:

```python
def test_your_feature():
    """Test description."""
    print("\nTesting your feature...")
    try:
        from src.your_module import your_function
        
        result = your_function("test input")
        
        if result != expected:
            print(f"✗ Test failed: {result}")
            return False
        
        print("✓ Your feature working")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
```

## Common Contribution Areas

### 1. Adding New Content Sources
File: `src/sources.py`

```python
SOURCES = {
    # Add new source
    "newsource": "https://newsource.com/feed.xml",
}
```

### 2. Improving Moderation
File: `src/moderation.py`

Add keywords to existing lists or create new categories:
```python
SENSITIVE_KEYWORDS = [
    # Add new sensitive keywords
    "new_keyword",
]
```

### 3. Enhancing Prompts
File: `src/generator.py`

Improve persona context or prompt generation:
```python
def get_persona_context() -> str:
    """Update persona tone or style."""
    # Your improvements
```

### 4. UI Improvements
File: `src/main.py`

Enhance templates or add new routes:
```python
@app.route('/new-feature')
def new_feature():
    """New feature description."""
    # Implementation
```

### 5. Documentation
Files: `README.md`, `VERIFICATION.md`, `QUICKREF.md`

- Fix typos
- Add examples
- Clarify instructions
- Add troubleshooting tips

## Pull Request Guidelines

### PR Title
Use descriptive titles:
- ✅ "Add support for Reddit RSS feeds"
- ✅ "Fix Turkish character encoding in comments"
- ✅ "Improve error handling in scheduler"
- ❌ "Update code"
- ❌ "Fix bug"

### PR Description
Include:
1. **What**: What does this PR do?
2. **Why**: Why is this change needed?
3. **How**: How does it work?
4. **Testing**: How did you test it?

Example:
```markdown
## What
Adds support for fetching articles from Reddit RSS feeds.

## Why
Users requested ability to include Reddit posts in daily content.

## How
- Added reddit.com RSS parser to sources.py
- Updated moderation to handle Reddit-specific content
- Added configuration for subreddit selection

## Testing
- ✅ Installation tests pass
- ✅ DRY_RUN mode tested with Reddit feed
- ✅ Moderation correctly filters political subreddits
```

### PR Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass (`python3 test_installation.py`)
- [ ] DRY_RUN mode tested
- [ ] Documentation updated (if needed)
- [ ] No secrets or credentials committed
- [ ] Commit messages are clear

## Bug Reports

### Before Reporting
1. Search existing issues
2. Test with latest code
3. Verify it's not a configuration issue

### Bug Report Template
```markdown
## Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11]
- Docker version: [e.g., 24.0.0]
- DRY_RUN: [true/false]

## Logs
```
Paste relevant logs here
```
```

## Feature Requests

### Feature Request Template
```markdown
## Problem
Describe the problem or use case

## Proposed Solution
Your suggested implementation

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Any other relevant information
```

## Questions?

- Check [README.md](README.md) for setup instructions
- Review [VERIFICATION.md](VERIFICATION.md) for implementation details
- See [QUICKREF.md](QUICKREF.md) for common commands
- Open a GitHub issue for questions

## Thank You!

Your contributions make LinkedIn Agent better for everyone. We appreciate your time and effort!
