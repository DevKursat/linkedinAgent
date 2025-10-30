#!/bin/bash
# LinkedIn Agent - Automated Deployment Script
# This script automates the deployment of the LinkedIn Agent on a production server

set -e

echo "=========================================="
echo "LinkedIn Agent - Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker is installed"

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi
print_success "Docker Compose is installed"

# Check if .env file exists
if [ ! -f .env ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env
    print_success ".env file created"
    print_info "Please edit .env file and add your credentials:"
    echo "  - LINKEDIN_CLIENT_ID"
    echo "  - LINKEDIN_CLIENT_SECRET"
    echo "  - GEMINI_API_KEY"
    echo "  - FLASK_SECRET_KEY"
    echo ""
    echo "After editing .env, run this script again."
    exit 0
fi
print_success ".env file exists"

# Check required environment variables
source .env
missing_vars=()

if [ -z "$LINKEDIN_CLIENT_ID" ]; then
    missing_vars+=("LINKEDIN_CLIENT_ID")
fi

if [ -z "$LINKEDIN_CLIENT_SECRET" ]; then
    missing_vars+=("LINKEDIN_CLIENT_SECRET")
fi

if [ -z "$GEMINI_API_KEY" ]; then
    missing_vars+=("GEMINI_API_KEY")
fi

if [ -z "$FLASK_SECRET_KEY" ] || [ "$FLASK_SECRET_KEY" = "change-this-in-production" ]; then
    missing_vars+=("FLASK_SECRET_KEY")
fi

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing or invalid environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please edit .env file and set these variables."
    exit 1
fi
print_success "All required environment variables are set"

# Create data directory if it doesn't exist
if [ ! -d data ]; then
    mkdir -p data
    print_success "Created data directory"
fi

# Check if style files exist
style_files=("data/about_me.md" "data/style.md" "data/style_comment.md")
for file in "${style_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_info "Creating $file..."
        touch "$file"
        echo "# Please edit this file to customize your bot" > "$file"
    fi
done
print_success "Style files are ready"

# Determine which compose file to use
COMPOSE_FILE="docker-compose.yml"
if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    print_info "Using production compose file"
else
    print_info "Using development compose file"
fi

# Pull latest images if using production compose
if [ "$COMPOSE_FILE" = "docker-compose.prod.yml" ]; then
    print_info "Pulling latest images from GitHub Container Registry..."
    docker compose -f $COMPOSE_FILE pull || print_error "Failed to pull images (they may not exist yet)"
fi

# Stop existing containers
if docker compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    print_info "Stopping existing containers..."
    docker compose -f $COMPOSE_FILE down
    print_success "Containers stopped"
fi

# Build or start containers
print_info "Starting containers..."
if [ "$COMPOSE_FILE" = "docker-compose.yml" ]; then
    docker compose -f $COMPOSE_FILE up -d --build
else
    docker compose -f $COMPOSE_FILE up -d
fi

# Wait for services to be ready
print_info "Waiting for services to start..."
sleep 5

# Check if containers are running
if docker compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    print_success "Containers are running"
    echo ""
    echo "=========================================="
    print_success "Deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Open http://localhost:5000 in your browser"
    echo "2. Click 'Login with LinkedIn' to authenticate"
    echo "3. Monitor logs: docker compose -f $COMPOSE_FILE logs -f"
    echo "4. Check health: curl http://localhost:5000/health"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker compose -f $COMPOSE_FILE logs -f"
    echo "  - Stop services: docker compose -f $COMPOSE_FILE down"
    echo "  - Restart services: docker compose -f $COMPOSE_FILE restart"
    echo "  - View status: docker compose -f $COMPOSE_FILE ps"
    echo ""
else
    print_error "Deployment failed - containers are not running"
    echo ""
    echo "Check logs for errors:"
    echo "  docker compose -f $COMPOSE_FILE logs"
    exit 1
fi
