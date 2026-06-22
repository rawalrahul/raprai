<#
  scripts/sign.ps1 - Authenticode code signer for RAPR AI.

  Signs any file (web_app.exe, installer .exe) with the best certificate available.

  Certificate resolution order (first match wins):
    1. RAPR_SIGN_PFX          path to a .pfx/.p12 file (real CA cert).
       RAPR_SIGN_PFX_PASSWORD password for that PFX (optional if none).
    2. RAPR_SIGN_THUMBPRINT   SHA1 thumbprint of a cert already in CurrentUser\My
                              (use for EV/hardware-token or pre-imported CA certs).
    3. Self-signed dev cert (CN=RAPR AI) in CurrentUser\My - DEV ONLY.
       Does NOT clear SmartScreen / "Unknown Publisher". Ship a real CA cert.
    4. None found - warns and skips (build continues unsigned).

  A real OV/EV Authenticode cert (steps 1-2) is what actually removes the
  "Windows protected your PC" SmartScreen prompt. Self-signed never does.

  Usage:
    powershell -File scripts/sign.ps1 -File web_app.dist\web_app.exe
    powershell -File scripts/sign.ps1 -File installer_output\RAPR_AI_Setup_2.0.0.exe
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$File,

    [string]$TimestampServer = 'http://timestamp.digicert.com',

    [string]$Description = 'RAPR AI'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $File)) {
    Write-Host "  SIGN: file not found, skipping: $File"
    exit 0
}

function Resolve-SigningCert {
    # 1. PFX from env
    if ($env:RAPR_SIGN_PFX -and (Test-Path $env:RAPR_SIGN_PFX)) {
        Write-Host "  SIGN: using PFX from RAPR_SIGN_PFX"
        if ($env:RAPR_SIGN_PFX_PASSWORD) {
            $sec = ConvertTo-SecureString $env:RAPR_SIGN_PFX_PASSWORD -AsPlainText -Force
            return Get-PfxCertificate -FilePath $env:RAPR_SIGN_PFX -Password $sec
        }
        return Get-PfxCertificate -FilePath $env:RAPR_SIGN_PFX
    }

    # 2. Thumbprint of an installed cert (EV / hardware token / imported CA)
    if ($env:RAPR_SIGN_THUMBPRINT) {
        $tp = $env:RAPR_SIGN_THUMBPRINT -replace '\s', ''
        $c = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $tp } | Select-Object -First 1
        if ($c) {
            Write-Host "  SIGN: using installed cert by thumbprint (real CA expected)"
            return $c
        }
        Write-Host "  SIGN: RAPR_SIGN_THUMBPRINT set but no matching cert in CurrentUser\My"
    }

    # 3. Self-signed dev fallback
    $dev = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like '*RAPR AI*' } | Select-Object -First 1
    if ($dev) {
        Write-Host "  SIGN: WARNING - using SELF-SIGNED dev cert. Will NOT clear SmartScreen."
        Write-Host "        Set RAPR_SIGN_PFX or RAPR_SIGN_THUMBPRINT to a real CA cert for release."
        return $dev
    }

    return $null
}

$cert = Resolve-SigningCert
if (-not $cert) {
    Write-Host "  SIGN: no certificate available - skipping signing of $File"
    exit 0
}

try {
    $result = Set-AuthenticodeSignature -FilePath $File -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $TimestampServer
    Write-Host "  SIGN: $File -> $($result.Status) ($($result.StatusMessage))"
    if ($result.Status -ne 'Valid') {
        Write-Host "  SIGN: WARNING - status not 'Valid' (self-signed reports UnknownError until trusted)."
    }
} catch {
    Write-Host "  SIGN: ERROR signing $File - $($_.Exception.Message)"
    # Non-fatal: let the build continue and ship unsigned rather than break CI.
    exit 0
}
