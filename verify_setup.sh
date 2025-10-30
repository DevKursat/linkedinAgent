#!/bin/bash
# LinkedIn Agent - Setup Verification Script
# Run this before deploying to verify your environment is correctly configured

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "LinkedIn Agent - Setup Verification"
echo -e "==========================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Function to check requirements
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
        return 0
    else
        echo -e "${RED}✗ $1${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check Python
echo "Checking Python..."
python --version &> /dev/null
check "Python is installed"

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if (( $(echo "$PYTHON_VERSION >= 3.10" | bc -l) )); then
    check "Python version is 3.10+"
else
    warn "Python version is $PYTHON_VERSION, recommended 3.10+"
fi

# Check Docker
echo ""
echo "Checking Docker..."
docker --version &> /dev/null
check "Docker is installed"

docker info &> /dev/null
check "Docker daemon is running"

# Check Docker Compose
docker compose version &> /dev/null
check "Docker Compose is installed"

# Check files
echo ""
echo "Checking project files..."

[ -f "requirements.txt" ]
check "requirements.txt exists"

[ -f "Dockerfile" ]
check "Dockerfile exists"

[ -f "docker-compose.yml" ]
check "docker-compose.yml exists"

[ -f "docker-compose.prod.yml" ]
check "docker-compose.prod.yml exists"

[ -f ".env.example" ]
check ".env.example exists"

[ -f "pytest.ini" ]
check "pytest.ini exists"

[ -d "src" ]
check "src directory exists"

[ -d "tests" ]
check "tests directory exists"

[ -f "tests/__init__.py" ]
check "tests/__init__.py exists"

[ -f "tests/conftest.py" ]
check "tests/conftest.py exists"

# Check .env file
echo ""
echo "Checking environment configuration..."

if [ -f ".env" ]; then
    check ".env file exists"
    
    # Read .env file safely - load values without executing
    # This only reads for verification, doesn't actually execute the values
    # Regex pattern for valid environment variable names (POSIX shell compatible)
    valid_key_regex='[A-Za-z_][A-Za-z0-9_]*'
    key_value_pattern="^(${valid_key_regex})=(.*)$"
    
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        
        # Extract key and value, handling spaces in values
        # The key is validated by the regex capture group, so additional validation is unnecessary
        if [[ "$line" =~ $key_value_pattern ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            
            # Export without evaluating value (safe - no command substitution)
            export "$key=$value"
        fi
    done < .env
    
    # Check required variables
    if [ -z "$LINKEDIN_CLIENT_ID" ]; then
        warn "LINKEDIN_CLIENT_ID is not set or empty"
    else
        check "LINKEDIN_CLIENT_ID is set"
    fi
    
    if [ -z "$LINKEDIN_CLIENT_SECRET" ]; then
        warn "LINKEDIN_CLIENT_SECRET is not set or empty"
    else
        check "LINKEDIN_CLIENT_SECRET is set"
    fi
    
    if [ -z "$GEMINI_API_KEY" ]; then
        warn "GEMINI_API_KEY is not set or empty"
    else
        check "GEMINI_API_KEY is set"
    fi
    
    if [ -z "$FLASK_SECRET_KEY" ]; then
        warn "FLASK_SECRET_KEY is not set"
    elif [ "$FLASK_SECRET_KEY" = "change-this-in-production" ]; then
        warn "FLASK_SECRET_KEY is still default value - change it!"
    else
        check "FLASK_SECRET_KEY is set"
    fi
    
    # Check optional but important variables
    if [ -z "$LINKEDIN_REDIRECT_URI" ]; then
        warn "LINKEDIN_REDIRECT_URI not set"
    else
        info "LINKEDIN_REDIRECT_URI: $LINKEDIN_REDIRECT_URI"
    fi
    
    if [ "$DRY_RUN" = "false" ]; then
        warn "DRY_RUN is disabled - system will make real posts"
    else
        info "DRY_RUN is enabled - safe for testing"
    fi
else
    warn ".env file not found - copy .env.example to .env and configure"
    ERRORS=$((ERRORS + 1))
fi

# Check data directory
echo ""
echo "Checking data directory..."

if [ -d "data" ]; then
    check "data directory exists"
    
    [ -f "data/about_me.md" ]
    check "data/about_me.md exists"
    
    [ -f "data/style.md" ]
    check "data/style.md exists"
    
    [ -f "data/style_comment.md" ]
    check "data/style_comment.md exists"
else
    warn "data directory not found - will be created on first run"
fi

# Test Docker Compose configuration
echo ""
echo "Validating Docker Compose configuration..."

docker compose config &> /dev/null
check "docker-compose.yml is valid"

docker compose -f docker-compose.prod.yml config &> /dev/null
check "docker-compose.prod.yml is valid"

# Test Python syntax
echo ""
echo "Checking Python syntax..."

python -m compileall -q src/ tests/ &> /dev/null
check "Python syntax is valid"

# Summary
echo ""
echo -e "${BLUE}=========================================="
echo "Verification Summary"
echo -e "==========================================${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! System is ready for deployment.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review your .env configuration"
    echo "  2. Run: ./deploy.sh (for development) or ./deploy.sh prod (for production)"
    echo "  3. Open http://localhost:5000 and authenticate with LinkedIn"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found. Review them before deploying.${NC}"
    echo ""
    echo "System can be deployed, but review warnings above."
    exit 0
else
    echo -e "${RED}✗ $ERRORS error(s) found. Fix them before deploying.${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warning(s) also found.${NC}"
    fi
    echo ""
    echo "Fix the errors above before attempting deployment."
    exit 1
fi
