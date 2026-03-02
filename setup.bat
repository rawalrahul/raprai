@echo off
:: Always run from the folder that contains this script,
:: regardless of where it was launched from (shortcut, cmd, Explorer, etc.)
cd /d "%~dp0"
chcp 65001 >nul
setlocal enabledelayedexpansion

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
    echo .env found - checking configuration...
)
echo.

:: -----------------------------------------------------------------------
:: Check TELEGRAM_BOT_TOKEN
:: Python exits 0 if the key exists and is non-blank, 1 if missing/blank.
:: This avoids temp files and set /p-from-file, which are unreliable on
:: Windows when the file has no trailing newline.
:: -----------------------------------------------------------------------
set "NEED_TOKEN=0"
python -c "from dotenv import dotenv_values; import sys; sys.exit(0 if dotenv_values('.env').get('TELEGRAM_BOT_TOKEN','').strip() else 1)"
if errorlevel 1 set "NEED_TOKEN=1"

if "!NEED_TOKEN!"=="1" (
    echo No TELEGRAM_BOT_TOKEN found in .env.
    echo.
    echo ================================================================
    echo   STEP 1 -- Create a Telegram Bot
    echo ================================================================
    echo.
    echo   1. Open Telegram (phone or desktop)
    echo   2. Search for @BotFather and open the chat
    echo   3. Send:  /newbot
    echo   4. Enter a display name for your bot
    echo      e.g.  My Assistant
    echo   5. Enter a username ending in 'bot'
    echo      e.g.  myassistant_bot
    echo   6. BotFather will reply with your token. It looks like:
    echo.
    echo        1234567890:ABCDefghIJKlmNOPqrstUVwxyz
    echo.
    echo   Copy the entire token string (everything after "Use this token").
    echo ================================================================
    echo.
    set /p "NEW_TOKEN=  Paste your bot token here and press Enter: "
    echo.

    :: Write token to .env using Python for safe handling of special chars
    echo !NEW_TOKEN!| python -c "import sys,re; t=sys.stdin.read().strip(); f=open('.env','r',encoding='utf-8'); c=f.read(); f.close(); c=re.sub(r'^TELEGRAM_BOT_TOKEN=.*','TELEGRAM_BOT_TOKEN='+t,c,flags=re.MULTILINE) if 'TELEGRAM_BOT_TOKEN=' in c else c.rstrip()+'\nTELEGRAM_BOT_TOKEN='+t+'\n'; open('.env','w',encoding='utf-8').write(c)"

    echo   Bot token saved to .env
    echo.
) else (
    echo   TELEGRAM_BOT_TOKEN ... OK
)

:: -----------------------------------------------------------------------
:: Check ALLOWED_USER_IDS  (independent of token check)
:: -----------------------------------------------------------------------
set "NEED_IDS=0"
python -c "from dotenv import dotenv_values; import sys; sys.exit(0 if dotenv_values('.env').get('ALLOWED_USER_IDS','').strip() else 1)"
if errorlevel 1 set "NEED_IDS=1"

if "!NEED_IDS!"=="1" (
    echo ================================================================
    echo   STEP 2 -- Get your Telegram User ID
    echo ================================================================
    echo.
    echo   Your User ID tells the bot who is allowed to send it commands.
    echo.
    echo   1. Open Telegram and search for @userinfobot
    echo   2. Open the chat and send:  /start
    echo   3. It replies instantly with your numeric ID, e.g.:
    echo.
    echo        Your ID: 123456789
    echo.
    echo   Copy just the number (no spaces, no "Your ID:" prefix).
    echo   To allow multiple people, separate IDs with commas:
    echo        123456789,987654321
    echo ================================================================
    echo.
    set /p "NEW_IDS=  Paste your User ID and press Enter: "
    echo.

    echo !NEW_IDS!| python -c "import sys,re; t=sys.stdin.read().strip(); f=open('.env','r',encoding='utf-8'); c=f.read(); f.close(); c=re.sub(r'^ALLOWED_USER_IDS=.*','ALLOWED_USER_IDS='+t,c,flags=re.MULTILINE) if 'ALLOWED_USER_IDS=' in c else c.rstrip()+'\nALLOWED_USER_IDS='+t+'\n'; open('.env','w',encoding='utf-8').write(c)"

    echo   User ID saved to .env
    echo.
) else (
    echo   ALLOWED_USER_IDS ........ OK
)

:: -- Done --
echo.
echo ================================================================
echo   Setup complete! Launch the app with:
echo ================================================================
echo.
echo   launch.bat                       - start with default directory
echo   launch.bat C:\projects\myapp     - start in a specific folder
echo   launch.bat "C:\My Projects\app"  - use quotes for paths with spaces
echo.
echo   Opens the web UI at http://localhost:8000
echo   Telegram bot runs simultaneously in the same process.
echo.
pause
