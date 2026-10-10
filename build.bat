@echo off
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       RAPR AI  —  Build Script               ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Clean previous build
if exist web_app.dist (
    echo  Removing old dist folder...
    rmdir /s /q web_app.dist
)
if exist web_app.build (
    echo  Removing old build cache...
    rmdir /s /q web_app.build
)
if exist installer_output (
    echo  Removing old installer...
    rmdir /s /q installer_output
)

:: ── Generate self-signed cert and sign exe (bypasses Smart App Control) ──
:: Skipped in CI (GitHub Actions sets CI=true): a throwaway runner cert adds nothing.
if not defined CI (
    echo  Generating self-signed code signing certificate...
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\gen_cert.ps1"
    echo  Certificate ready.
    echo.
)

:: ── Generate .ico from rapr-logo.png (needed by Inno Setup + shortcuts) ──────
echo  Generating logo.ico from rapr-logo.png...
python -c "from PIL import Image; img=Image.open('rapr-logo.png'); img.save('logo.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if errorlevel 1 (
    echo  WARNING: Could not generate logo.ico — Pillow may not be installed.
    echo  Run: pip install Pillow
) else (
    echo  logo.ico created successfully.
)

echo.
echo  Starting Nuitka compilation...
echo  (This may take 10-20 minutes)
echo.

:: -- Optional semantic vector memory: bundle ONLY if fastembed is installed --
::    On build envs without it (e.g. Python 3.14, no onnxruntime wheel) these
::    flags are skipped and the app ships with keyword/FTS memory only.
set "VEC_FLAGS="
python -c "import fastembed, onnxruntime" 2>nul && set "VEC_FLAGS=--include-package=fastembed --include-package=onnxruntime --include-package=tokenizers --include-package=numpy --include-package=huggingface_hub --include-package-data=onnxruntime --include-package-data=fastembed"
if defined VEC_FLAGS (echo  Semantic vector memory: ENABLED in this build) else (echo  Semantic vector memory: NOT bundled - keyword/FTS only)

:: -- WhatsApp (neonize): bundle the package and its native library. Nuitka does not
::    copy DLLs as package data, so the DLL is added explicitly next to the package.
set "WA_FLAGS="
set "NEONIZE_DIR="
for /f "delims=" %%i in ('python -c "import importlib.util,os;s=importlib.util.find_spec('neonize');print(os.path.dirname(s.origin) if s else '')" 2^>nul') do set "NEONIZE_DIR=%%i"
if defined NEONIZE_DIR if exist "%NEONIZE_DIR%\neonize-windows-amd64.dll" set "WA_FLAGS=--include-package=neonize --include-package=segno --include-data-files=%NEONIZE_DIR%\neonize-windows-amd64.dll=neonize\neonize-windows-amd64.dll"
if defined WA_FLAGS (echo  WhatsApp support: ENABLED in this build) else (echo  WhatsApp support: NOT bundled - pip install neonize)

:: --assume-yes-for-downloads: Nuitka otherwise stops to ask before fetching its
:: C compiler / dependency tools, which hangs unattended (CI) builds.
python -m nuitka --standalone --assume-yes-for-downloads --enable-plugin=tk-inter ^
    --include-data-files=rapr-logo.png=rapr-logo.png ^
    --include-data-files=logo-watermark-dark.png=logo-watermark-dark.png ^
    --include-data-files=logo-watermark-light.png=logo-watermark-light.png ^
    --windows-icon-from-ico=logo.ico ^
    --windows-console-mode=disable ^
    --include-package=pptx ^
    --include-package=docx ^
    --include-package=openpyxl ^
    --include-package=reportlab ^
    --include-package=pypdf ^
    --include-package=pystray ^
    --include-package=PIL ^
    --nofollow-import-to=helm.plugins.* ^
    --nofollow-import-to=google.genai ^
    --include-package=google.genai ^
    --include-module=helm.mcp.composio_mcp ^
    --include-module=helm.mcp.zapier_mcp ^
    %VEC_FLAGS% ^
    %WA_FLAGS% ^
    %NUITKA_EXTRA% ^
    web_app.py

if errorlevel 1 (
    echo.
    echo  ERROR: Nuitka compilation failed. Check the errors above.
    if not defined CI pause
    exit /b 1
)

echo.
echo  Signing web_app.exe with self-signed certificate...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\sign_exe.ps1"
echo.

echo  Copying additional files into dist...

:: Copy integrations (dynamically loaded .py files)
xcopy /E /I /Q integrations web_app.dist\integrations
if errorlevel 1 echo  WARNING: Could not copy integrations folder.

:: Plugins and skills are NOT bundled — they're installed via the marketplace at runtime.
:: The helm\plugins and helm\skills directories are created on first launch if needed.
:: Explicitly remove them from dist in case Nuitka somehow included them.
if exist web_app.dist\helm\plugins (
    echo  Removing bundled plugins from dist - should be marketplace-only...
    rmdir /s /q web_app.dist\helm\plugins
)
if exist web_app.dist\helm\skills (
    echo  Removing bundled skills from dist - should be marketplace-only...
    rmdir /s /q web_app.dist\helm\skills
)

:: Development-only directories — never ship to users
if exist web_app.dist\chrome-extension (
    echo  Removing dev-only: chrome-extension
    rmdir /s /q web_app.dist\chrome-extension
)
if exist web_app.dist\marketplace (
    echo  Removing dev-only: marketplace
    rmdir /s /q web_app.dist\marketplace
)
if exist web_app.dist\rapr-oauth-proxy (
    echo  Removing dev-only: rapr-oauth-proxy
    rmdir /s /q web_app.dist\rapr-oauth-proxy
)
if exist web_app.dist\scripts (
    echo  Removing dev-only: scripts
    rmdir /s /q web_app.dist\scripts
)
if exist web_app.dist\unpacked_plan (
    echo  Removing dev-only: unpacked_plan
    rmdir /s /q web_app.dist\unpacked_plan
)
if exist web_app.dist\__pycache__ (
    echo  Removing dev-only: __pycache__
    rmdir /s /q web_app.dist\__pycache__
)

:: Copy frontend2 (separated frontend served at runtime)
if exist frontend2 (
    xcopy /E /I /Q frontend2 web_app.dist\frontend2
    if errorlevel 1 echo  WARNING: Could not copy frontend2 folder.
)

:: Copy MCP server configuration
if exist mcp_servers.json (
    copy /Y mcp_servers.json web_app.dist\ >nul
    echo  Copied mcp_servers.json
)

:: Copy setup and readme for end users
copy /Y setup_dist.bat web_app.dist\ >nul 2>&1
copy /Y README_DIST.md web_app.dist\ >nul 2>&1

:: Copy app icon into dist (used by shortcuts)
if exist logo.ico (
    copy /Y logo.ico web_app.dist\ >nul
    echo  Copied logo.ico into dist
)

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║         Nuitka build complete!               ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── Inno Setup installer (optional) ──────────────────────────────────────
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
    echo  Inno Setup found — building installer...
    echo.
    "%ISCC%" installer.iss
    if errorlevel 1 (
        echo.
        echo  WARNING: Installer build failed. Check errors above.
        echo  The dist folder is still usable — just no .exe installer.
    ) else (
        echo.
        echo  Installer created: installer_output\RAPR_AI_Setup_2.0.0.exe
        echo  Signing installer...
        powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\sign.ps1" -File "installer_output\RAPR_AI_Setup_2.0.0.exe"
    )
) else (
    echo  Inno Setup not found — skipping installer creation.
    echo  Install from: https://jrsoftware.org/isinfo.php
    echo  Then rerun build.bat to generate the installer.
)

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║            All done!                         ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Dist folder:  web_app.dist\
echo  Test:         cd web_app.dist ^& web_app.exe
echo.
if exist installer_output\RAPR_AI_Setup_2.0.0.exe (
    echo  Installer:    installer_output\RAPR_AI_Setup_2.0.0.exe
    echo.
)
if not defined CI pause
