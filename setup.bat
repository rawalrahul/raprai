@echo off
setlocal

echo === Claude Remote — Setup ===
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: Install dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

:: Create .env from example if missing
if not exist .env (
    echo.
    echo Creating .env from .env.example ...
    copy .env.example .env >nul
    echo Done. Edit .env and fill in TELEGRAM_BOT_TOKEN and ALLOWED_USER_IDS.
) else (
    echo .env already exists — skipping copy.
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Open .env and set TELEGRAM_BOT_TOKEN and ALLOWED_USER_IDS
echo   2. Run:  python telegram_claude_bot.py
echo.
pause
