@echo off
REM Start script for local development on Windows

echo Starting LinkedIn Bot...

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure your credentials
    exit /b 1
)

REM Install dependencies
echo Checking dependencies...
pip install -q -r requirements.txt

REM Initialize database
echo Initializing database...
python -c "from database import init_db; init_db()"

REM Start both services
echo Starting services...
start "LinkedIn Bot Web" python app.py
timeout /t 2 /nobreak >nul
start "LinkedIn Bot Worker" python scheduler.py

echo.
echo LinkedIn Bot is running!
echo Web UI: http://localhost:5000
echo.
echo Close the command windows to stop the services
