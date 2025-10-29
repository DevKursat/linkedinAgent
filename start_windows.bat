@echo off
REM LinkedIn Agent - Windows Quick Start Script
REM This script helps Windows users start the application easily

echo.
echo ============================================================
echo   LinkedIn Agent - Windows Quick Start
echo ============================================================
echo.

REM Check if Docker Desktop is running
echo [1/5] Checking Docker Desktop...
docker version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker Desktop is not running!
    echo.
    echo Please:
    echo   1. Open Docker Desktop from Start Menu
    echo   2. Run it as Administrator (Right-click - Run as administrator)
    echo   3. Wait for it to fully start (green icon in system tray)
    echo   4. Run this script again
    echo.
    echo For detailed help, see: WINDOWS_DOCKER_COZUM.md
    echo.
    pause
    exit /b 1
)
echo    OK - Docker is running
echo.

REM Check if .env file exists
echo [2/5] Checking .env configuration...
if not exist .env (
    echo.
    echo .env file not found. Creating from template...
    copy .env.example .env >nul
    echo    Created .env file
    echo.
    echo IMPORTANT: Please edit .env file and fill in:
    echo   - LINKEDIN_CLIENT_ID
    echo   - LINKEDIN_CLIENT_SECRET
    echo   - GEMINI_API_KEY
    echo.
    echo After editing .env, run this script again.
    echo.
    notepad .env
    pause
    exit /b 0
)
echo    OK - .env file exists
echo.

REM Run pre-flight check
echo [3/5] Running Docker pre-flight check...
python check_docker.py
if errorlevel 1 (
    echo.
    echo Pre-flight check failed. Please fix the issues above.
    echo For detailed help, see: WINDOWS_DOCKER_COZUM.md
    echo.
    pause
    exit /b 1
)
echo.

REM Stop any existing containers
echo [4/5] Cleaning up old containers...
docker compose down >nul 2>&1
echo    OK - Cleanup complete
echo.

REM Build and start containers
echo [5/5] Building and starting LinkedIn Agent...
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start containers!
    echo.
    echo Try these steps:
    echo   1. Make sure Docker Desktop is running as Administrator
    echo   2. Check the error messages above
    echo   3. See WINDOWS_DOCKER_COZUM.md for detailed troubleshooting
    echo.
    pause
    exit /b 1
)
echo.
echo ============================================================
echo   SUCCESS! LinkedIn Agent is now running
echo ============================================================
echo.
echo Opening the web interface...
timeout /t 2 >nul
start http://localhost:5000
echo.
echo You can now:
echo   - Click "Login with LinkedIn" to authenticate
echo   - View logs: docker compose logs -f
echo   - Stop: docker compose down
echo.
echo For help, see:
echo   - README_TR.md (Turkish)
echo   - BASLATMA_KOMUTLARI.md (Detailed guide)
echo   - WINDOWS_DOCKER_COZUM.md (Windows troubleshooting)
echo.
pause
