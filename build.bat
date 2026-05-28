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
echo  Generating self-signed code signing certificate...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\gen_cert.ps1"
echo  Certificate ready.
echo.

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

python -m nuitka --standalone --enable-plugin=tk-inter ^
    --include-data-dir=helm/frontend=helm/frontend ^
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
    web_app.py

if errorlevel 1 (
    echo.
    echo  ERROR: Nuitka compilation failed. Check the errors above.
    pause
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
pause
