; ═══════════════════════════════════════════════════════════════════════════════
; RAPR AI — Inno Setup Installer Script
;
; Prerequisites:
;   1. Run build.bat first to produce web_app.dist\
;   2. Install Inno Setup 6: https://jrsoftware.org/isinfo.php
;   3. Open this file in Inno Setup Compiler and click Build → Compile
;      OR run from command line:
;        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;
; The installer will:
;   - Copy everything from web_app.dist\ into AppData\Local
;   - Create a Start Menu shortcut
;   - Create a Desktop shortcut (optional)
;   - Register an uninstaller
;   - Optionally run setup_dist.bat after install (installs Node.js etc.)
; ═══════════════════════════════════════════════════════════════════════════════

#define MyAppName "RAPR AI"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "RAPR AI"
#define MyAppURL "https://raprai.com"
#define MyAppExeName "web_app.exe"
#define MyAppIcon "rapr-logo.png"

[Setup]
; Unique AppId — DO NOT change this between versions (used for upgrades)
AppId={{8F3A6D2E-4B71-4C9A-B8E2-1D5F7A3C9E0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
; Install to user's local AppData — no admin required
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Allow user to choose desktop shortcut
AllowNoIcons=yes
; Output location and filename for the generated installer .exe
OutputDir=installer_output
OutputBaseFilename=RAPR_AI_Setup_{#MyAppVersion}
; App icon (built by build.bat from rapr-logo.png → logo.ico)
SetupIconFile=logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
; Require Windows 10+
MinVersion=10.0
; No admin required — installs to user-writable AppData\Local
PrivilegesRequired=lowest
; Nice modern look
WizardStyle=modern
; Uninstall settings
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\logo.ico
; Show a brief info page during install
LicenseFile=
InfoBeforeFile=installer_info.txt
; Allow upgrading over existing installation
UsePreviousAppDir=yes
; Process is killed via [Code] section before install/uninstall
CloseApplications=force
RestartApplications=yes
AppMutex=RAPR_AI_SingleInstance

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "rundeps"; Description: "Install required tools (Node.js, Pandoc, FFmpeg)"; GroupDescription: "Post-install:"; Flags: checkedonce

[Files]
; Include EVERYTHING from the Nuitka dist folder EXCEPT plugins and skills
; (plugins/skills are installed at runtime via the marketplace — never bundled)
Source: "web_app.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "helm\plugins\*,helm\skills\*,chrome-extension\*,marketplace\*,rapr-oauth-proxy\*,scripts\*,unpacked_plan\*,__pycache__\*"
; NOTE: web_app.dist\ must exist before compiling this script.
;       Run build.bat first!

[Icons]
; Start Menu shortcut (with app icon)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\logo.ico"; Comment: "Launch RAPR AI"
; Start Menu — open install folder
Name: "{group}\RAPR AI Folder"; Filename: "{app}"; Comment: "Open RAPR AI installation folder"
; Start Menu — uninstall
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (with app icon)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon; Comment: "Launch RAPR AI"

[Run]
; Run setup_dist.bat after install (if user checked the option)
Filename: "{app}\setup_dist.bat"; Description: "Install external dependencies (Node.js, Pandoc, etc.)"; Flags: nowait postinstall skipifsilent shellexec; Tasks: rundeps
; Offer to launch the app after install (interactive mode — user chooses)
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent unchecked; WorkingDir: "{app}"
; Auto-launch after silent upgrade (no user interaction)
Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifdoesntexist; WorkingDir: "{app}"; Check: IsSilentInstall

[Code]
// Return True if the installer was launched with /SILENT or /VERYSILENT
function IsSilentInstall(): Boolean;
begin
  Result := WizardSilent();
end;

// Kill any running RAPR AI process before install or uninstall
procedure KillRAPRAI();
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM web_app.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000);
end;

function InitializeSetup(): Boolean;
begin
  KillRAPRAI();
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  KillRAPRAI();
  Result := True;
end;

[UninstallDelete]
; Clean up runtime files that RAPR AI creates (not part of the install)
Type: files; Name: "{app}\.env"
Type: files; Name: "{app}\.vault_key"
Type: files; Name: "{app}\helmhq.db"
Type: files; Name: "{app}\helmhq.db-shm"
Type: files; Name: "{app}\helmhq.db-wal"
Type: files; Name: "{app}\.heartbeat_last"
Type: filesandordirs; Name: "{app}\chat_logs"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\helmpack_cache"
Type: filesandordirs; Name: "{app}\packages_cache"
Type: filesandordirs; Name: "{app}\packages_staging"
Type: dirifempty; Name: "{app}"

