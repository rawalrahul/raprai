@echo off
cd /d "%~dp0"
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       RAPR AI  —  First-Run Setup            ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  This script installs the external tools RAPR AI needs.
echo  Python is NOT required — it is already bundled in.
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
:: 1. NODE.JS  (needed for Word/PowerPoint file creation)
:: ════════════════════════════════════════════════════════════════════════════
echo  [1/6]  Checking Node.js...
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
        echo   │  3. Run the installer (default options are fine^)             │
        echo   │  4. Reopen this window and run setup_dist.bat again          │
        echo   └──────────────────────────────────────────────────────────────┘
        echo.
        echo   NOTE: Node.js is needed for Word (.docx^) and PowerPoint (.pptx^)
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
        timeout /t 2 /nobreak >nul
        node --version >nul 2>&1
        if errorlevel 1 (
            echo.
            echo   Node.js was installed but is not yet in PATH.
            echo   Please close this window, reopen it, and run setup_dist.bat again.
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
:: 2. NPM PACKAGES  (docx + pptxgenjs for document/slide creation)
:: ════════════════════════════════════════════════════════════════════════════
echo  [2/6]  Installing Node packages...
if defined NODE_MISSING (
    echo   Skipping — Node.js was not installed.
) else (
    node --version >nul 2>&1
    if errorlevel 1 (
        echo   Skipping — Node.js not available in this session.
        echo   Rerun setup_dist.bat after installing Node.js to complete this step.
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
:: 3. PANDOC  (optional — for reading existing .docx files)
:: ════════════════════════════════════════════════════════════════════════════
echo  [3/6]  Checking Pandoc (optional)...
pandoc --version >nul 2>&1
if errorlevel 1 (
    echo   Pandoc not found.  Attempting automatic install via winget...
    call :winget_install "JohnMacFarlane.Pandoc" "Pandoc"
    if errorlevel 1 (
        echo.
        echo   Pandoc could not be installed automatically.
        echo   It is optional — install it later from https://pandoc.org/installing.html
        echo   (only needed for reading existing .docx files^)
    ) else (
        echo   Pandoc installed.
    )
) else (
    echo     Pandoc found.
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: 4. FFMPEG  (optional — for voice message transcription)
:: ════════════════════════════════════════════════════════════════════════════
echo  [4/6]  Checking FFmpeg (optional — for voice messages)...
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
:: 5. TESSERACT OCR  (optional — for scanned PDF documents)
:: ════════════════════════════════════════════════════════════════════════════
echo  [5/6]  Checking Tesseract OCR (optional)...
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
:: 6. PLAYWRIGHT CLI  (optional — for AI-driven browser automation)
:: ════════════════════════════════════════════════════════════════════════════
echo  [6/6]  Checking Playwright CLI (optional — for browser automation)...
if defined NODE_MISSING (
    echo   Skipping — Node.js was not installed.
) else (
    node --version >nul 2>&1
    if errorlevel 1 (
        echo   Skipping — Node.js not available in this session.
    ) else (
        npx @playwright/cli --version >nul 2>&1
        if errorlevel 1 (
            echo   Installing Playwright CLI and Chromium browser...
            call npm install -g @playwright/cli@latest --silent
            if errorlevel 1 (
                echo   WARNING: Playwright CLI install failed.
                echo   Browser automation tasks will not be available.
                echo   Install later: npm install -g @playwright/cli@latest
            ) else (
                echo   Installing Chromium for Playwright...
                npx playwright install chromium >nul 2>&1
                if errorlevel 1 (
                    echo   WARNING: Chromium install failed. Run manually:
                    echo     npx playwright install chromium
                ) else (
                    echo   Playwright CLI + Chromium installed.
                )
            )
        ) else (
            echo     Playwright CLI found.
        )
    )
)
echo.


:: ════════════════════════════════════════════════════════════════════════════
:: DONE
:: ════════════════════════════════════════════════════════════════════════════
echo  ╔══════════════════════════════════════════════╗
echo  ║            Setup complete!                   ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Next step: double-click web_app.exe to start RAPR AI.
echo.
echo  The web UI will open at http://localhost:8000
echo  A setup wizard will guide you through configuring
echo  your API keys, Telegram bot, and PIN protection.
echo.
if defined NODE_MISSING (
    echo  ⚠  Remember to install Node.js and rerun setup_dist.bat
    echo     to enable Word and PowerPoint file creation.
    echo.
)
pause
