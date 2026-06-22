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

  FAIL-CLOSED: if a release signing identity (RAPR_SIGN_PFX or RAPR_SIGN_THUMBPRINT)
  is set but cannot be resolved, this script EXITS NON-ZERO and never falls back to
  the self-signed dev cert. That prevents silently shipping a build signed with the
  wrong identity (or unsigned) while the operator believes it was release-signed.
  The dev fallback is only used when NO release env var is set at all.

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

# Release intent: operator explicitly configured a release signing identity.
# When true, any failure is fatal (never downgrade to self-signed, never ship unsigned).
$ReleaseIntent = [bool]($env:RAPR_SIGN_PFX -or $env:RAPR_SIGN_THUMBPRINT)

function Fail-Sign([string]$msg) {
    Write-Host "  SIGN: ERROR - $msg"
    # Fatal only when a release identity was requested; otherwise let the build
    # continue unsigned (dev builds).
    if ($ReleaseIntent) { exit 1 } else { exit 0 }
}

if (-not (Test-Path $File)) {
    # A missing artifact when release-signing is a hard error.
    if ($ReleaseIntent) { Fail-Sign "file not found: $File" }
    Write-Host "  SIGN: file not found, skipping: $File"
    exit 0
}

function Resolve-SigningCert {
    # 1. PFX from env (release identity)
    if ($env:RAPR_SIGN_PFX) {
        if (-not (Test-Path $env:RAPR_SIGN_PFX)) {
            Fail-Sign "RAPR_SIGN_PFX set but file not found: $env:RAPR_SIGN_PFX"
        }
        Write-Host "  SIGN: using PFX from RAPR_SIGN_PFX"
        try {
            if ($env:RAPR_SIGN_PFX_PASSWORD) {
                $sec = ConvertTo-SecureString $env:RAPR_SIGN_PFX_PASSWORD -AsPlainText -Force
                return Get-PfxCertificate -FilePath $env:RAPR_SIGN_PFX -Password $sec
            }
            return Get-PfxCertificate -FilePath $env:RAPR_SIGN_PFX
        } catch {
            Fail-Sign "could not load PFX ($($_.Exception.Message))"
        }
    }

    # 2. Thumbprint of an installed cert (release identity: EV / hardware token / imported CA)
    if ($env:RAPR_SIGN_THUMBPRINT) {
        $tp = $env:RAPR_SIGN_THUMBPRINT -replace '\s', ''
        $c = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $tp } | Select-Object -First 1
        if ($c) {
            Write-Host "  SIGN: using installed cert by thumbprint (real CA expected)"
            return $c
        }
        Fail-Sign "RAPR_SIGN_THUMBPRINT set but no matching cert in CurrentUser\My"
    }

    # 3. Self-signed dev fallback - ONLY reachable when no release env var is set.
    #    Require a real, currently-valid code-signing key with an exact subject.
    $dev = Get-ChildItem Cert:\CurrentUser\My | Where-Object {
        $_.Subject -eq 'CN=RAPR AI' -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date)
    } | Select-Object -First 1
    if ($dev) {
        Write-Host "  SIGN: WARNING - using SELF-SIGNED dev cert. Will NOT clear SmartScreen."
        Write-Host "        Set RAPR_SIGN_PFX or RAPR_SIGN_THUMBPRINT to a real CA cert for release."
        return $dev
    }

    return $null
}

$cert = Resolve-SigningCert
if (-not $cert) {
    # No release env var was set (release path would have exited above), so this is
    # a dev build with no usable cert: skip, non-fatal.
    Write-Host "  SIGN: no certificate available - skipping signing of $File"
    exit 0
}

try {
    $result = Set-AuthenticodeSignature -FilePath $File -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $TimestampServer
    Write-Host "  SIGN: $File -> $($result.Status) ($($result.StatusMessage))"
    if ($result.Status -ne 'Valid') {
        # A non-Valid signature during a release build must fail the build. (Self-signed
        # dev certs legitimately report UnknownError until trusted, so only fatal here
        # when a release identity was requested.)
        if ($ReleaseIntent) {
            Fail-Sign "release signature status is '$($result.Status)', expected 'Valid'"
        }
        Write-Host "  SIGN: WARNING - status not 'Valid' (self-signed reports UnknownError until trusted)."
    }
} catch {
    Fail-Sign "signing failed for $File - $($_.Exception.Message)"
}
