@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

set "LOG=%~dp0setup.log"
set "ERRORS=0"
echo RAPR AI Setup Log - %date% %time% > "%LOG%"

echo.
echo  RAPR AI - Dependency Setup
echo  ---------------------------
echo  Installing optional tools silently. This may take a few minutes.
echo.

:: ════════════════════════════════════════════════════════════════════════
:: HELPER: silent winget install
:: ════════════════════════════════════════════════════════════════════════
goto :skip_helper
:winget_install
  winget --version >nul 2>&1
  if errorlevel 1 ( exit /b 1 )
  winget install --id %~1 --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
  exit /b %errorlevel%
:skip_helper


:: ════════════════════════════════════════════════════════════════════════
:: 1. PANDOC
:: ════════════════════════════════════════════════════════════════════════
echo  [1/3]  Pandoc...
pandoc --version >nul 2>&1
if errorlevel 1 (
    call :winget_install "JohnMacFarlane.Pandoc"
    if errorlevel 1 (
        echo         FAILED - install manually from pandoc.org
        set "ERRORS=1"
    ) else (
        echo         Installed.
    )
) else (
    echo         OK
)


:: ════════════════════════════════════════════════════════════════════════
:: 2. FFMPEG
:: ════════════════════════════════════════════════════════════════════════
echo  [2/3]  FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    call :winget_install "Gyan.FFmpeg"
    if errorlevel 1 (
        echo         FAILED - install manually from ffmpeg.org
        set "ERRORS=1"
    ) else (
        echo         Installed.
    )
) else (
    echo         OK
)


:: ════════════════════════════════════════════════════════════════════════
:: 3. TESSERACT
:: ════════════════════════════════════════════════════════════════════════
echo  [3/3]  Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    call :winget_install "UB-Mannheim.TesseractOCR"
    if errorlevel 1 (
        echo         FAILED - install manually from github.com/UB-Mannheim/tesseract
        set "ERRORS=1"
    ) else (
        echo         Installed.
    )
) else (
    echo         OK
)


:: ════════════════════════════════════════════════════════════════════════
:: DONE - only pause if there were errors
:: ════════════════════════════════════════════════════════════════════════
echo.
if "%ERRORS%"=="1" (
    echo  Some tools could not be installed automatically.
    echo  Download the Setup Guide from: rapr-ai-website.vercel.app/download
    echo.
    pause
) else (
    echo  Setup complete. Launching RAPR AI...
    timeout /t 2 /nobreak >nul
)
