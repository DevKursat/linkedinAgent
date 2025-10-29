@echo off
REM ============================================================
REM   TAM OTONOM LINKEDIN AI AGENT BAŞLATICI - WINDOWS
REM   (FULLY AUTONOMOUS LINKEDIN AI AGENT LAUNCHER - WINDOWS)
REM ============================================================
REM
REM Bu dosyaya çift tıklayarak LinkedIn AI Agent'ınızı 
REM kusursuz ve hatasız başlatabilirsiniz.
REM
REM Double-click this file to start your LinkedIn AI Agent
REM flawlessly and error-free.
REM ============================================================

title LinkedIn AI Agent Launcher

REM Python'u bul (Find Python)
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
) else (
    where python3 >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=python3
    ) else (
        where py >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            set PYTHON_CMD=py
        ) else (
            echo.
            echo HATA: Python bulunamadi!
            echo ERROR: Python not found!
            echo.
            echo Lutfen Python 3.8+ yukleyin (Please install Python 3.8+):
            echo https://www.python.org/downloads/
            echo.
            pause
            exit /b 1
        )
    )
)

REM Proje dizinine gec (Change to project directory)
cd /d "%~dp0"

REM Python launcher'i calistir (Run Python launcher)
%PYTHON_CMD% BASLAT_AI_AGENT.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Agent baslatma hatasi! (Agent launch error!)
    echo.
    pause
    exit /b 1
)

pause
