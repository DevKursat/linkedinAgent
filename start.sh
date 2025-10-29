#!/bin/bash
# LinkedIn Agent - Quick Start Script for Linux/macOS
# This script helps users start the application easily

set -e

echo ""
echo "============================================================"
echo "  LinkedIn Agent - Quick Start"
echo "============================================================"
echo ""

# Check if Docker is running
echo "[1/5] Checking Docker..."
if ! docker version >/dev/null 2>&1; then
    echo ""
    echo "ERROR: Docker is not running!"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please:"
        echo "  1. Open Docker Desktop from Applications"
        echo "  2. Wait for it to fully start"
        echo "  3. Run this script again"
    else
        echo "Please start Docker:"
        echo "  sudo systemctl start docker"
        echo ""
        echo "Then run this script again."
    fi
    echo ""
    exit 1
fi
echo "   OK - Docker is running"
echo ""

# Check if .env file exists
echo "[2/5] Checking .env configuration..."
if [ ! -f .env ]; then
    echo ""
    echo ".env file not found. Creating from template..."
    cp .env.example .env
    echo "   Created .env file"
    echo ""
    echo "IMPORTANT: Please edit .env file and fill in:"
    echo "  - LINKEDIN_CLIENT_ID"
    echo "  - LINKEDIN_CLIENT_SECRET"
    echo "  - GEMINI_API_KEY"
    echo ""
    echo "After editing .env, run this script again."
    echo ""
    
    # Try to open the file in an editor
    if command -v nano >/dev/null 2>&1; then
        nano .env
    elif command -v vim >/dev/null 2>&1; then
        vim .env
    else
        echo "Please edit .env manually with your preferred editor."
    fi
    exit 0
fi
echo "   OK - .env file exists"
echo ""

# Run pre-flight check
echo "[3/5] Running Docker pre-flight check..."
if ! python3 check_docker.py; then
    echo ""
    echo "Pre-flight check failed. Please fix the issues above."
    echo "For help, see: BASLATMA_KOMUTLARI.md"
    echo ""
    exit 1
fi
echo ""

# Stop any existing containers
echo "[4/5] Cleaning up old containers..."
docker compose down >/dev/null 2>&1 || true
echo "   OK - Cleanup complete"
echo ""

# Build and start containers
echo "[5/5] Building and starting LinkedIn Agent..."
if ! docker compose up -d --build; then
    echo ""
    echo "ERROR: Failed to start containers!"
    echo ""
    echo "Try these steps:"
    echo "  1. Make sure Docker is running"
    echo "  2. Check the error messages above"
    echo "  3. See BASLATMA_KOMUTLARI.md for detailed troubleshooting"
    echo ""
    exit 1
fi

echo ""
echo "============================================================"
echo "  SUCCESS! LinkedIn Agent is now running"
echo "============================================================"
echo ""
echo "Opening the web interface..."
sleep 2

# Open browser based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:5000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost:5000 >/dev/null 2>&1 &
    else
        echo "Please open: http://localhost:5000"
    fi
fi

echo ""
echo "You can now:"
echo "  - Click 'Login with LinkedIn' to authenticate"
echo "  - View logs: docker compose logs -f"
echo "  - Stop: docker compose down"
echo ""
echo "For help, see:"
echo "  - README.md (English)"
echo "  - README_TR.md (Turkish)"
echo "  - BASLATMA_KOMUTLARI.md (Detailed guide)"
echo ""
