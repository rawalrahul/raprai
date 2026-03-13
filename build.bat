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

echo.
echo  Starting Nuitka compilation...
echo  (This may take 10-20 minutes)
echo.

python -m nuitka --standalone --enable-plugin=tk-inter --include-data-dir=helm/frontend=helm/frontend --include-data-files=logo.png=logo.png web_app.py

if errorlevel 1 (
    echo.
    echo  ERROR: Nuitka compilation failed. Check the errors above.
    pause
    exit /b 1
)

echo.
echo  Copying additional files into dist...

:: Copy integrations (dynamically loaded .py files)
xcopy /E /I /Q integrations web_app.dist\integrations
if errorlevel 1 echo  WARNING: Could not copy integrations folder.

:: Copy setup and readme for end users
copy /Y setup_dist.bat web_app.dist\ >nul 2>&1
copy /Y README_DIST.md web_app.dist\ >nul 2>&1

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
        echo  Installer created: installer_output\RAPR_AI_Setup_1.0.0.exe
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
if exist installer_output\RAPR_AI_Setup_1.0.0.exe (
    echo  Installer:    installer_output\RAPR_AI_Setup_1.0.0.exe
    echo.
)
pause
