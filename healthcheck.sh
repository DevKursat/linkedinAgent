#!/bin/bash
# LinkedIn Agent - Health Check Script
# This script checks if the LinkedIn Agent is running properly

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "LinkedIn Agent - Health Check"
echo "=============================="
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Determine which compose file is in use
COMPOSE_FILE="docker-compose.yml"
if docker compose -f docker-compose.prod.yml ps &> /dev/null && docker compose -f docker-compose.prod.yml ps | grep -q "linkedinagent"; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

# Check if containers are running
echo ""
echo "Container Status:"
echo "-----------------"

if docker compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    worker_status=$(docker compose -f $COMPOSE_FILE ps | grep worker | grep -q "Up" && echo "running" || echo "stopped")
    web_status=$(docker compose -f $COMPOSE_FILE ps | grep web | grep -q "Up" && echo "running" || echo "stopped")
    
    if [ "$worker_status" = "running" ]; then
        echo -e "${GREEN}✓ Worker: Running${NC}"
    else
        echo -e "${RED}✗ Worker: Stopped${NC}"
    fi
    
    if [ "$web_status" = "running" ]; then
        echo -e "${GREEN}✓ Web: Running${NC}"
    else
        echo -e "${RED}✗ Web: Stopped${NC}"
    fi
else
    echo -e "${RED}✗ No containers are running${NC}"
    exit 1
fi

# Check web service health endpoint
echo ""
echo "Service Health:"
echo "---------------"

if curl -sf http://localhost:5000/health &> /dev/null; then
    health_response=$(curl -s http://localhost:5000/health)
    echo -e "${GREEN}✓ Web service is healthy${NC}"
    echo "  Response: $health_response"
else
    echo -e "${RED}✗ Web service is not responding${NC}"
    echo "  Try: curl http://localhost:5000/health"
fi

# Check disk space for data directory
echo ""
echo "Storage:"
echo "--------"

data_dir="./data"
if [ -d "$data_dir" ]; then
    disk_usage=$(du -sh "$data_dir" 2>/dev/null | cut -f1)
    echo -e "${GREEN}✓ Data directory: $disk_usage${NC}"
    
    # Check if database exists
    if [ -f "$data_dir/bot.db" ]; then
        db_size=$(du -h "$data_dir/bot.db" | cut -f1)
        echo -e "${GREEN}✓ Database: $db_size${NC}"
    else
        echo -e "${YELLOW}⚠ Database file not found${NC}"
    fi
else
    echo -e "${RED}✗ Data directory not found${NC}"
fi

# Show recent logs
echo ""
echo "Recent Logs (last 10 lines):"
echo "----------------------------"
docker compose -f $COMPOSE_FILE logs --tail=10 2>&1 | tail -10

echo ""
echo "=============================="
echo "Health check complete"
echo ""
echo "For detailed logs, run:"
echo "  docker compose -f $COMPOSE_FILE logs -f"
