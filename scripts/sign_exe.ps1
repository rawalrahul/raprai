<#
  scripts/sign_exe.ps1 — back-compat wrapper. Signs the Nuitka-built web_app.exe.
  Real signing logic lives in scripts/sign.ps1 (cert resolution, timestamp, fallbacks).
#>
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\sign.ps1" -File 'web_app.dist\web_app.exe'
