#!/bin/bash

# Start script for local development
# This starts both the web service and worker in the background

echo "Starting LinkedIn Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your credentials"
    exit 1
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "Initializing database..."
python -c "from database import init_db; init_db()"

# Start web service
echo "Starting web service on port 5000..."
python app.py &
WEB_PID=$!

# Wait a bit for web service to start
sleep 2

# Start worker
echo "Starting scheduler worker..."
python scheduler.py &
WORKER_PID=$!

echo ""
echo "LinkedIn Bot is running!"
echo "Web UI: http://localhost:5000"
echo "Web PID: $WEB_PID"
echo "Worker PID: $WORKER_PID"
echo ""
echo "Press Ctrl+C to stop both services"

# Function to handle shutdown
cleanup() {
    echo ""
    echo "Stopping LinkedIn Bot..."
    kill $WEB_PID 2>/dev/null
    kill $WORKER_PID 2>/dev/null
    echo "Stopped."
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT TERM

# Wait for both processes
wait
