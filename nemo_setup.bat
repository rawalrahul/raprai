@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  NemoClaw Setup Script for Windows
REM  Installs all WSL dependencies for NemoClaw + OpenShell
REM ============================================================
REM
REM  Prerequisites (install these BEFORE running this script):
REM    1. Windows 10/11 with WSL2 enabled (run: wsl --install)
REM    2. Docker Desktop with WSL2 integration enabled
REM    3. Ubuntu set as default WSL distribution
REM
REM  What this script does (inside WSL/Ubuntu):
REM    - Installs Node.js 22 LTS
REM    - Installs dos2unix and git
REM    - Installs OpenShell CLI v0.0.10
REM    - Clones NemoClaw from GitHub
REM    - Installs NemoClaw globally via npm
REM    - Creates the CRLF fix-and-onboard script
REM    - Runs NemoClaw onboarding (interactive)
REM
REM  Usage:
REM    Right-click this file -> Run as administrator
REM    OR open CMD/PowerShell as admin and run: nemo_setup.bat
REM
REM ============================================================

title NemoClaw Setup

echo.
echo  ============================================================
echo   NemoClaw Setup for Windows
echo   NVIDIA Sandboxed AI Agent (Nemotron 3 Super 120B)
echo  ============================================================
echo.

REM --- Check if WSL is available ---
echo [1/8] Checking WSL...
wsl --status >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: WSL is not installed or not running.
    echo  Run this in PowerShell as Administrator:
    echo    wsl --install
    echo  Then restart your PC and run this script again.
    echo.
    pause
    exit /b 1
)
echo       WSL is available.

REM --- Check if Docker is running ---
echo [2/8] Checking Docker...
wsl -e bash -lc "docker info >/dev/null 2>&1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: Docker is not running inside WSL.
    echo  Make sure:
    echo    1. Docker Desktop is installed and running on Windows
    echo    2. WSL2 integration is enabled in Docker Desktop:
    echo       Settings ^> Resources ^> WSL Integration ^> Toggle ON Ubuntu
    echo    3. Click Apply ^& Restart in Docker Desktop
    echo.
    pause
    exit /b 1
)
echo       Docker is running.

REM --- Install Node.js 22 ---
echo [3/8] Installing Node.js 22 in WSL...
wsl -e bash -lc "node --version 2>/dev/null | grep -q 'v2[2-9]\|v[3-9]' && echo 'Node.js already installed' || (curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs)"
if %ERRORLEVEL% neq 0 (
    echo  WARNING: Node.js installation may have failed. Check manually.
)
echo       Node.js setup complete.

REM --- Install additional tools ---
echo [4/8] Installing dos2unix and git...
wsl -e bash -lc "sudo apt update -qq && sudo apt install -y -qq dos2unix git 2>/dev/null"
echo       Tools installed.

REM --- Install OpenShell CLI ---
echo [5/8] Installing OpenShell CLI v0.0.10...
wsl -e bash -lc "if command -v openshell >/dev/null 2>&1; then echo 'OpenShell already installed'; else curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | OPENSHELL_VERSION=v0.0.10 sh && echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc; fi"
echo       OpenShell setup complete.

REM --- Clone NemoClaw ---
echo [6/8] Cloning NemoClaw repository...
wsl -e bash -lc "export PATH=\"$HOME/.local/bin:$PATH\" && if [ -d ~/NemoClaw ]; then echo 'NemoClaw already cloned, pulling latest...'; cd ~/NemoClaw && git pull; else cd ~ && git clone --config core.autocrlf=false https://github.com/NVIDIA/NemoClaw.git && cd ~/NemoClaw && sudo npm install -g .; fi"
echo       NemoClaw ready.

REM --- Create fix-and-onboard.sh ---
echo [7/8] Creating CRLF fix script...
wsl -e bash -lc "cat > ~/NemoClaw/fix-and-onboard.sh << 'SCRIPT'\n#!/bin/bash\nset -euo pipefail\necho \"[*] Starting CRLF fixer in background...\"\n(\nwhile true; do\nfor dir in /tmp/nemoclaw-build-*/; do\nif [ -d \"$dir\" ]; then\nfind \"$dir\" -type f -exec sed -i 's/\\r$//' {} + 2>/dev/null\nfi\ndone\nsleep 0.2\ndone\n) &\nFIXER_PID=$!\ntrap 'kill $FIXER_PID 2>/dev/null' EXIT\necho \"[*] CRLF fixer running (PID: $FIXER_PID)\"\necho \"[*] Starting NemoClaw onboarding...\"\necho \"\"\nnemoclaw onboard\necho \"\"\necho \"[*] Onboarding complete!\"\necho \"[*] Run: nemoclaw <sandbox-name> connect\"\necho \"[*] Then: openclaw tui\"\nSCRIPT\nchmod +x ~/NemoClaw/fix-and-onboard.sh"
echo       Fix script created.

REM --- Run onboarding ---
echo [8/8] Starting NemoClaw onboarding...
echo.
echo  ============================================================
echo   The interactive NemoClaw setup wizard will now start.
echo   You will need:
echo     - A name for your sandbox (e.g., mynemo)
echo     - An NVIDIA API key from https://build.nvidia.com
echo   The wizard will guide you through 7 steps.
echo  ============================================================
echo.
pause

wsl -e bash -lc "export PATH=\"$HOME/.local/bin:$PATH\" && cd ~/NemoClaw && ./fix-and-onboard.sh"

echo.
echo  ============================================================
echo   NemoClaw setup complete!
echo.
echo   To use NemoClaw:
echo     1. Open Ubuntu terminal (or run: wsl)
echo     2. nemoclaw mynemo connect
echo     3. openclaw tui
echo.
echo   To run a one-shot command from Ubuntu host:
echo     openclaw agent --agent main --message "hello"
echo.
echo   RAPR AI will detect NemoClaw automatically on next restart.
echo  ============================================================
echo.
pause
