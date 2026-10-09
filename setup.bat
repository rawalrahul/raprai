@echo off
cd /d "%~dp0"
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║          RAPR AI  —  First-Run Setup         ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  This script installs everything RAPR AI needs.
echo  It is safe to run more than once.
echo.

:: ════════════════════════════════════════════════════════════════════════════
:: HELPER: try a winget install if winget is available
:: Usage: call :winget_install "WingetID" "Display Name"
:: ════════════════════════════════════════════════════════════════════════════
goto :skip_helper

:winget_install
  winget --version >nul 2>&1
  if errorlevel 1 (
    echo     winget not available — skipping auto-install for %~2
    exit /b 1
  )
  echo   Installing %~2 via winget...
  winget install --id %~1 --silent --accept-package-agreements --accept-source-agreements
  exit /b %errorlevel%

:skip_helper


:: ════════════════════════════════════════════════════════════════════════════
:: 1. PYTHON
:: ════════════════════════════════════════════════════════════════════════════
echo  [1/8]  Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Python was not found.  Attempting automatic install via winget...
    call :winget_install "Python.Python.3.12" "Python 3.12"
    if errorlevel 1 (
        echo.
        echo   ┌──────────────────────────────────────────────────────────────┐
        echo   │  ACTION REQUIRED — Install Python manually                   │
        echo   │                                                               │
        echo   │  1. Visit: https://www.python.org/downloads/                 │
        echo   │  2. Download Python 3.10 or newer                            │
        echo   │  3. Run the installer and tick "Add Python to PATH"          │
        echo   │  4. Reopen this window and run setup.bat again               │
        echo   └──────────────────────────────────────────────────────────────┘
        echo.
        pause
        exit /b 1
    )
    rem Refresh PATH so the newly installed Python is visible
    for /f "tokens=*" %%i in ('where python 2^>nul') do set "PYTHON_PATH=%%i"
    if "!PYTHON_PATH!"=="" (
        echo.
        echo   Python was installed but is not yet in PATH.
        echo   Please close this window, reopen it, and run setup.bat again.
        echo.
        pause
        exit /b 1
    )
    echo   Python installed successfully.
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo     %%v found.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 2. NODE.JS
:: ════════════════════════════════════════════════════════════════════════════
echo  [2/8]  Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Node.js was not found.  Attempting automatic install via winget...
    call :winget_install "OpenJS.NodeJS.LTS" "Node.js LTS"
    if errorlevel 1 (
        echo.
        echo   ┌──────────────────────────────────────────────────────────────┐
        echo   │  ACTION REQUIRED — Install Node.js manually                  │
        echo   │                                                               │
        echo   │  1. Visit: https://nodejs.org/en/download/                   │
        echo   │  2. Download the LTS installer for Windows                   │
        echo   │  3. Run the installer ^(default options are fine^)             │
        echo   │  4. Reopen this window and run setup.bat again               │
        echo   └──────────────────────────────────────────────────────────────┘
        echo.
        echo   NOTE: Node.js is needed for Word ^(.docx^) and PowerPoint ^(.pptx^)
        echo   file creation.  RAPR AI will still run without it, but those
        echo   features will not work until Node.js is installed.
        echo.
        set /p "SKIP_NODE=  Skip Node.js and continue anyway? [y/N]: "
        if /i "!SKIP_NODE!" neq "y" (
            pause
            exit /b 1
        )
        set "NODE_MISSING=1"
    ) else (
        rem Give Node a moment to register in PATH, then recheck
        timeout /t 2 /nobreak >nul
        node --version >nul 2>&1
        if errorlevel 1 (
            echo.
            echo   Node.js was installed but is not yet in PATH.
            echo   Please close this window, reopen it, and run setup.bat again.
            echo.
            pause
            exit /b 1
        )
        echo   Node.js installed successfully.
    )
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo     Node.js %%v found.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 3. PANDOC  (optional — used by docx skill for text extraction)
:: ════════════════════════════════════════════════════════════════════════════
echo  [3/8]  Checking Pandoc (optional)...
pandoc --version >nul 2>&1
if errorlevel 1 (
    echo   Pandoc not found.  Attempting automatic install via winget...
    call :winget_install "JohnMacFarlane.Pandoc" "Pandoc"
    if errorlevel 1 (
        echo.
        echo   Pandoc could not be installed automatically.
        echo   It is optional — install it later from https://pandoc.org/installing.html
        echo   ^(only needed for reading existing .docx files^)
    ) else (
        echo   Pandoc installed.
    )
) else (
    echo     Pandoc found.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 4. PYTHON PACKAGES
:: ════════════════════════════════════════════════════════════════════════════
echo  [4/8]  Installing Python packages...
echo.

echo     Core server dependencies (requirements.txt)...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: pip install failed.  Check the errors above and try again.
    pause
    exit /b 1
)

echo     Skill dependencies (markitdown, Pillow, pytesseract, pdf2image)...
python -m pip install "markitdown[pptx]" Pillow pytesseract pdf2image --quiet
if errorlevel 1 (
    echo   WARNING: Some skill packages failed to install.
    echo   RAPR AI will still run but PDF/PPTX skills may be limited.
)

echo     Voice support (openai-whisper, static-ffmpeg)...
python -m pip install openai-whisper static-ffmpeg --quiet
if errorlevel 1 (
    echo   WARNING: Whisper/FFmpeg install failed.
    echo   Voice messages will not work until these are installed.
)

echo     Done.
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 5. NPM GLOBAL PACKAGES  (docx + pptxgenjs for document/slide creation)
:: ════════════════════════════════════════════════════════════════════════════
echo  [5/8]  Installing Node packages...
if defined NODE_MISSING (
    echo   Skipping — Node.js was not installed.
) else (
    node --version >nul 2>&1
    if errorlevel 1 (
        echo   Skipping — Node.js not available in this session.
        echo   Rerun setup.bat after installing Node.js to complete this step.
    ) else (
        echo     Installing docx and pptxgenjs globally...
        call npm install -g docx pptxgenjs --silent
        if errorlevel 1 (
            echo   WARNING: npm install failed.  Word/PowerPoint creation from
            echo   scratch may not work until this is resolved.
        ) else (
            echo     Done.
        )
    )
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 6. FFMPEG  (optional — used by Whisper for voice transcription)
:: ════════════════════════════════════════════════════════════════════════════
echo  [6/8]  Checking FFmpeg (optional — for voice messages)...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo   FFmpeg not found.  Attempting automatic install via winget...
    call :winget_install "Gyan.FFmpeg" "FFmpeg"
    if errorlevel 1 (
        echo.
        echo   FFmpeg could not be installed automatically.
        echo   It is optional — only needed for Telegram voice message transcription.
        echo   Install later from: https://ffmpeg.org/download.html
    ) else (
        echo   FFmpeg installed.
    )
) else (
    echo     FFmpeg found.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 7. TESSERACT OCR  (optional — used by pdf skill for scanned documents)
:: ════════════════════════════════════════════════════════════════════════════
echo  [7/8]  Checking Tesseract OCR (optional)...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo   Tesseract not found.  Attempting automatic install via winget...
    call :winget_install "UB-Mannheim.TesseractOCR" "Tesseract OCR"
    if errorlevel 1 (
        echo.
        echo   Tesseract could not be installed automatically.
        echo   It is optional — only needed for OCR on scanned PDF files.
        echo   Install later from: https://github.com/UB-Mannheim/tesseract/wiki
    ) else (
        echo   Tesseract installed.
    )
) else (
    echo     Tesseract found.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 7. CREATE .env IF MISSING
:: ════════════════════════════════════════════════════════════════════════════
echo  [8/8]  Checking .env...
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo     Created .env from .env.example
    ) else (
        type nul > .env
        echo     Created empty .env
    )
) else (
    echo     .env already exists — skipping.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: DONE
:: ════════════════════════════════════════════════════════════════════════════
echo  ╔══════════════════════════════════════════════╗
echo  ║            Setup complete!                   ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Next step: run launch.bat to start RAPR AI.
echo.
echo  The web UI will open at http://localhost:8000
echo  A setup wizard will guide you through configuring
echo  your Telegram bot token and other settings.
echo.
if defined NODE_MISSING (
    echo  ⚠  Remember to install Node.js and rerun setup.bat
    echo     to enable Word and PowerPoint file creation.
    echo.
)
pause
