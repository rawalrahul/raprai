@echo off
setlocal

echo === My Personal Assistant — Setup ===
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
echo   (python-telegram-bot, fastapi, uvicorn, python-dotenv)
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

:: Check if .env has been configured (token placeholder still present = not set up yet)
findstr /C:"TELEGRAM_BOT_TOKEN=" .env | findstr /V /C:"TELEGRAM_BOT_TOKEN=your" >nul 2>&1
for /f "tokens=2 delims==" %%A in ('findstr "TELEGRAM_BOT_TOKEN" .env') do set TOKEN_VAL=%%A
if "%TOKEN_VAL%"=="" (
    echo NOTE: TELEGRAM_BOT_TOKEN is not set in .env yet.
    echo Open .env and fill in:
    echo   TELEGRAM_BOT_TOKEN=your_token_here
    echo   ALLOWED_USER_IDS=your_telegram_user_id
    echo.
    echo Once configured, run setup.bat again to launch the app.
    pause
    exit /b 0
)

echo Launching web_app.py ...
echo.
echo   Web UI  →  http://localhost:8000
echo   Telegram bot is also active simultaneously.
echo.
echo Close this window to stop the app.
echo.
python web_app.py
