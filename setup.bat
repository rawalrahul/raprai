@echo off
:: Always run from the folder that contains this script,
:: regardless of where it was launched from (shortcut, cmd, Explorer, etc.)
cd /d "%~dp0"
chcp 65001 >nul

echo === Helm HQ - Setup ===
echo.

:: -- Check Python --
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: -- Install Python dependencies --
echo Installing Python dependencies...
echo   (python-telegram-bot, fastapi, uvicorn, python-dotenv, python-multipart, croniter, aiofiles)
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)
echo.

:: -- Create .env if missing --
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo Created .env from .env.example
    ) else (
        type nul > .env
        echo Created empty .env
    )
) else (
    echo .env already exists - skipping.
)
echo.

:: -- Done --
echo ================================================================
echo   Setup complete! Run launch.bat to start Helm HQ.
echo ================================================================
echo.
echo   The web UI will open at http://localhost:8000
echo   Follow the setup wizard in your browser to configure your
echo   Telegram bot token, user ID, and other settings.
echo.
pause
