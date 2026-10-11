# RAPR AI on Windows, from source: one command in PowerShell.
#
#   irm https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-windows.ps1 | iex
#
# Installs Python 3.12 with winget if needed, downloads RAPR into
# %LOCALAPPDATA%\rapr-ai, installs its packages, and adds "RAPR AI" to the
# Start menu and desktop plus a "rapr" command. Open "RAPR AI" to start it (it
# opens in your browser; its tray icon has Quit). Run the command again to update.
#
# Your chats and settings live in %LOCALAPPDATA%\RAPR AI, the same folder the
# Windows installer (.exe) uses, so you can switch between the two.
#
# The "rapr" command: rapr start | stop | open | status | logs | update | uninstall
#
# Options (environment variables):
#   RAPR_REF=<branch or tag>   what to install (default: main)
#   RAPR_SOURCE_DIR=<folder>   use this checkout instead of downloading (tests)
#   RAPR_NO_OPEN=1             don't start RAPR at the end (tests)
#   RAPR_YES=1                 answer yes to questions (tests)
#
# Written to run in Windows PowerShell 5.1 as well as PowerShell 7. It never
# calls "exit" (with "irm | iex" that would close your PowerShell window).

function Install-RaprAI {
  # 'Continue': in Windows PowerShell 5.1 a native program writing to stderr would
  # otherwise stop the script. Exit codes are checked, and cmdlets that must
  # succeed say -ErrorAction Stop.
  $ErrorActionPreference = 'Continue'
  $ProgressPreference = 'SilentlyContinue'      # Invoke-WebRequest is very slow with the progress bar
  [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

  $Repo    = 'rawalrahul/raprai'
  $Ref     = if ($env:RAPR_REF) { $env:RAPR_REF } else { 'main' }
  $Home_   = Join-Path $env:LOCALAPPDATA 'rapr-ai'
  $AppDir  = Join-Path $Home_ 'app'
  $Venv    = Join-Path $Home_ 'venv'
  $BinDir  = Join-Path $Home_ 'bin'
  $DataDir = Join-Path $env:LOCALAPPDATA 'RAPR AI'

  function Say($m)  { Write-Host "==> $m" -ForegroundColor Yellow }
  function Ok($m)   { Write-Host " v  $m" -ForegroundColor Green }
  function Fail($m) { throw "RAPR install: $m" }
  function AskYes($q) {
    if ($env:RAPR_YES -eq '1') { return $true }
    $a = Read-Host "    $q [y/N]"
    return ($a -match '^[Yy]')
  }
  function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
  }
  function Find-Python {
    # Python 3.12 through the "py" launcher, or where the python.org / winget installer puts it.
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
      $p = & $py.Source -3.12 -c "import sys; print(sys.executable)" 2>$null
      if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() }
    }
    foreach ($c in @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
                     (Join-Path $env:ProgramFiles 'Python312\python.exe'))) {
      if (Test-Path $c) { return $c }
    }
    $any = Get-Command python -ErrorAction SilentlyContinue
    if ($any -and $any.Source -notlike '*WindowsApps*') {     # skip the Microsoft Store stub
      $v = & $any.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v -and $v.Trim() -eq '3.12') { return $any.Source }
    }
    return $null
  }

  if ($env:OS -ne 'Windows_NT') { Fail 'This installer is for Windows. On a Mac use scripts/install-mac.sh; on Linux, scripts/install-server.sh.' }
  Ok "Windows $([Environment]::OSVersion.Version)"

  # --- Python 3.12 -----------------------------------------------------------
  $python = Find-Python
  if (-not $python) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
      Fail 'Python 3.12 is needed. Install it from https://www.python.org/downloads/ (tick "Add to PATH"), then run this again.'
    }
    Say 'RAPR needs Python 3.12.'
    if (-not (AskYes 'Install Python 3.12 now with winget?')) {
      Fail 'Install Python 3.12 from https://www.python.org/downloads/, then run this again.'
    }
    & $winget.Source install -e --id Python.Python.3.12 --scope user --silent `
      --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-Path
    $python = Find-Python
    if (-not $python) { Fail "Python 3.12 didn't install. Install it from https://www.python.org/downloads/ and run this again." }
  }
  Ok "Python: $python"

  New-Item -ItemType Directory -Force -Path $Home_, $BinDir, $DataDir -ErrorAction Stop | Out-Null

  # --- Stop a running RAPR before replacing its files ---------------------------
  $running = Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$Home_*" }
  foreach ($p in $running) {
    Say "Stopping the running RAPR (process $($p.ProcessId)) to update it..."
    & taskkill /PID $p.ProcessId /T /F | Out-Null
  }

  # --- RAPR's code -----------------------------------------------------------
  if ($env:RAPR_SOURCE_DIR) {
    $AppDir = (Resolve-Path $env:RAPR_SOURCE_DIR).Path
    Ok "Using RAPR from $AppDir"
  } else {
    Say "Downloading RAPR ($Ref)..."
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("rapr-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp -ErrorAction Stop | Out-Null
    try {
      $zip = Join-Path $tmp 'rapr.zip'
      Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$Repo/archive/$Ref.zip" -OutFile $zip -ErrorAction Stop
      Expand-Archive -Path $zip -DestinationPath $tmp -Force -ErrorAction Stop
      $src = Get-ChildItem -Path $tmp -Directory | Select-Object -First 1
      if (-not $src -or -not (Test-Path (Join-Path $src.FullName 'web_app.py'))) { Fail 'The download looks wrong (no web_app.py).' }
      if (Test-Path $AppDir) { Remove-Item -Recurse -Force $AppDir -ErrorAction Stop }
      Move-Item -Path $src.FullName -Destination $AppDir -ErrorAction Stop
    } finally {
      Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    }
    $ver = (Select-String -Path (Join-Path $AppDir 'helm\version.py') -Pattern 'APP_VERSION = "([^"]+)"').Matches[0].Groups[1].Value
    Ok "RAPR $ver downloaded"
  }

  # --- Python packages -------------------------------------------------------
  $vpy  = Join-Path $Venv 'Scripts\python.exe'
  $vpyw = Join-Path $Venv 'Scripts\pythonw.exe'
  if (-not (Test-Path $vpy)) {
    Say 'Creating RAPR''s Python environment...'
    & $python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Fail 'Could not create the Python environment.' }
  }
  Say 'Installing RAPR''s Python packages (a few minutes the first time)...'
  & $vpy -m pip install --quiet --disable-pip-version-check --upgrade pip 2>&1 | Out-Host
  & $vpy -m pip install --quiet --disable-pip-version-check -r (Join-Path $AppDir 'requirements.txt') 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) { Fail 'Installing the Python packages failed (see the messages above).' }
  Ok 'Packages installed'

  # Paths written into the generated files, escaped for each language.
  $AppDirPy  = ConvertTo-Json $AppDir
  $DataDirPy = ConvertTo-Json $DataDir
  function Q($p) { "'" + $p.Replace("'", "''") + "'" }    # PowerShell single-quoted string

  # --- Launcher: opens RAPR, or just its window when it's already running ----
  $launch = Join-Path $Home_ 'launch.pyw'
  @"
# Written by install-windows.ps1. Opens RAPR AI: shows it if it's already running, else starts it.
import os, runpy, sys, urllib.request, webbrowser
APP = $AppDirPy
DATA = $DataDirPy
os.environ['RAPR_DATA_DIR'] = DATA
os.environ['RAPR_INSTALL_KIND'] = 'source-windows'
# pythonw.exe (no console window) gives Python no stdout/stderr, and uvicorn's
# logging calls sys.stdout.isatty() at startup. Send them to a log file instead.
if sys.stdout is None or sys.stderr is None:
    os.makedirs(os.path.join(DATA, 'logs'), exist_ok=True)
    _out = open(os.path.join(DATA, 'logs', 'console.log'), 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stdout or _out
    sys.stderr = sys.stderr or _out
try:
    port = open(os.path.join(DATA, 'web_port'), encoding='utf-8').read().strip()
    urllib.request.urlopen('http://127.0.0.1:%s/health' % port, timeout=2)
    if '--background' not in sys.argv:
        webbrowser.open('http://localhost:%s' % port)
    sys.exit(0)
except SystemExit:
    raise
except Exception:
    pass
os.chdir(APP)
sys.path.insert(0, APP)
sys.argv = [os.path.join(APP, 'web_app.py')]
runpy.run_path(sys.argv[0], run_name='__main__')
"@ | Set-Content -Path $launch -Encoding UTF8 -ErrorAction Stop

  # --- The "rapr" command ----------------------------------------------------
  $cli = Join-Path $Home_ 'rapr.ps1'
  @"
# RAPR AI on this PC (written by install-windows.ps1).
param([string]`$cmd = '')
`$Home_ = $(Q $Home_)
`$DataDir = $(Q $DataDir)
function Get-Rapr { Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe'" -ErrorAction SilentlyContinue | Where-Object { `$_.CommandLine -and `$_.CommandLine -like "*`$Home_*" } }
function Get-Port { if (Test-Path "`$DataDir\web_port") { (Get-Content "`$DataDir\web_port" -Raw).Trim() } else { '8000' } }
switch (`$cmd) {
  'start'  { if (Get-Rapr) { Start-Process "http://localhost:`$(Get-Port)" } else { Start-Process -FilePath $(Q $vpyw) -ArgumentList $(Q ('"' + $launch + '"')) -WorkingDirectory $(Q $AppDir) } }
  'open'   { Start-Process "http://localhost:`$(Get-Port)" }
  'stop'   { `$p = Get-Rapr; if (`$p) { foreach (`$x in `$p) { taskkill /PID `$x.ProcessId /T /F | Out-Null }; 'RAPR stopped.' } else { 'RAPR is not running.' } }
  'status' { if (Get-Rapr) { "RAPR is running at http://localhost:`$(Get-Port)" } else { 'RAPR is not running. Start it with: rapr start (or the RAPR AI shortcut)'; `$global:LASTEXITCODE = 1 } }
  'logs'   { foreach (`$l in @("`$DataDir\logs\helm.log", "`$DataDir\logs\console.log")) { if (Test-Path `$l) { "== `$l"; Get-Content `$l -Tail 80 } } }
  'update' { irm https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-windows.ps1 | iex }
  'uninstall' {
    `$a = Read-Host "Remove RAPR from this PC? Your chats and settings stay unless you type 'all' [yes/all/N]"
    if (`$a -ne 'yes' -and `$a -ne 'all') { 'Nothing removed.'; return }
    foreach (`$x in @(Get-Rapr)) { taskkill /PID `$x.ProcessId /T /F | Out-Null }
    Remove-Item -Force -ErrorAction SilentlyContinue "`$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RAPR AI.lnk", ([Environment]::GetFolderPath('Desktop') + '\RAPR AI.lnk')
    `$up = [Environment]::GetEnvironmentVariable('Path', 'User'); `$bin = "`$Home_\bin"
    [Environment]::SetEnvironmentVariable('Path', ((`$up -split ';' | Where-Object { `$_ -and `$_ -ne `$bin }) -join ';'), 'User')
    if (`$a -eq 'all') { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `$DataDir }
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `$Home_
    if (`$a -eq 'all') { 'RAPR and its data removed.' } else { "RAPR removed. Your data is still in `$DataDir" }
  }
  default { 'Usage: rapr start | stop | open | status | logs | update | uninstall' }
}
"@ | Set-Content -Path $cli -Encoding UTF8 -ErrorAction Stop
  "@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"$cli`" %*`r`n" |
    Set-Content -Path (Join-Path $BinDir 'rapr.cmd') -Encoding ASCII

  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if (-not $userPath) { $userPath = '' }
  if (($userPath -split ';') -notcontains $BinDir) {
    [Environment]::SetEnvironmentVariable('Path', (($userPath.TrimEnd(';') + ';' + $BinDir).TrimStart(';')), 'User')
  }
  $env:Path = $env:Path.TrimEnd(';') + ';' + $BinDir

  # --- Start menu and desktop shortcuts ----------------------------------------
  $shell = New-Object -ComObject WScript.Shell
  $icon = Join-Path $AppDir 'logo.ico'
  foreach ($lnk in @((Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\RAPR AI.lnk'),
                     (Join-Path ([Environment]::GetFolderPath('Desktop')) 'RAPR AI.lnk'))) {
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath = $vpyw
    $s.Arguments = '"' + $launch + '"'
    $s.WorkingDirectory = $AppDir
    if (Test-Path $icon) { $s.IconLocation = $icon }
    $s.Description = 'RAPR AI'
    $s.Save()
  }
  Ok 'Added "RAPR AI" to the Start menu and desktop, and the "rapr" command'

  Write-Host ''
  if ($env:RAPR_NO_OPEN -eq '1') {
    Write-Host 'RAPR AI is installed. Open "RAPR AI" from the Start menu.' -ForegroundColor Green
  } else {
    Start-Process -FilePath $vpyw -ArgumentList ('"' + $launch + '"') -WorkingDirectory $AppDir
    Write-Host 'RAPR AI is installed and starting. It opens in your browser in a few seconds.' -ForegroundColor Green
    Write-Host 'Next time, open "RAPR AI" from the Start menu or desktop.'
  }
  Write-Host 'Quit from the RAPR tray icon (or "rapr stop"). Run the install command again to update.'
  Write-Host 'Commands (in a new terminal): rapr status | rapr logs | rapr update | rapr uninstall'
}

Install-RaprAI
