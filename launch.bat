@echo off
setlocal

:: ============================================================
::  RAPR AI — Launcher
::
::  Usage:
::    launch.bat                        — use SESSION_CWD from .env (or script folder)
::    launch.bat C:\projects\website    — open in a specific folder (one-time override)
::    launch.bat "C:\My Projects\app"   — use quotes if the path has spaces
::
::  Works in both modes:
::    - Source mode: runs web_app.py with Python
::    - Bundled mode: runs RAPR_AI.exe directly
:: ============================================================

:: Always run from the folder where this .bat lives
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo   RAPR AI — Starting...
echo.

:: Check .env exists; create from example if not
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo   Created .env from template.
        echo   The setup wizard will guide you through configuration.
        echo.
    ) else (
        type nul > .env
        echo   Created empty .env — configure via the setup wizard.
        echo.
    )
)

:: If a path argument was given, override SESSION_CWD for this launch only
if not "%~1"=="" (
    set "SESSION_CWD=%~1"
    echo   Working directory: %~1
) else (
    echo   Working directory: from .env ^(or default^)
)

echo   Web UI: http://localhost:8000
echo   Press Ctrl+C to stop.
echo.

:: Detect mode: bundled .exe or source
if exist RAPR_AI.exe (
    RAPR_AI.exe
    goto :eof
)

:: Source mode — check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found and RAPR_AI.exe not present.
    echo   Run setup.bat first, or install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

if exist web_app.py (
    python web_app.py
) else (
    echo   ERROR: Could not find RAPR_AI.exe or web_app.py
    echo   Make sure you are running this from the RAPR AI folder.
    pause
    exit /b 1
)
