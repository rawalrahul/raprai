@echo off
setlocal

:: ============================================================
::  Claude Remote — Launcher
::
::  Usage:
::    launch.bat                        — use SESSION_CWD from .env (or script folder)
::    launch.bat C:\projects\website    — open in a specific folder (one-time override)
::    launch.bat "C:\My Projects\app"   — use quotes if the path has spaces
::
::  Tip: create a Windows shortcut to this file and add a path
::  in the "Target" field to get per-project launcher icons.
:: ============================================================

:: Always run from the folder where this .bat lives
cd /d "%~dp0"

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Run setup.bat first, or install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: Check .env exists
if not exist .env (
    echo ERROR: .env not found.
    echo Run setup.bat first to create and configure .env.
    pause
    exit /b 1
)

:: If a path argument was given, override SESSION_CWD for this launch only
if not "%~1"=="" (
    set "SESSION_CWD=%~1"
    echo Starting Claude Remote
    echo Working directory: %~1
) else (
    echo Starting Claude Remote
    echo Working directory: from .env ^(or default^)
)

echo.
echo Web UI : http://localhost:8000
echo Press Ctrl+C here to stop.
echo.

python web_app.py
