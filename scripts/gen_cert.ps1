$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like '*RAPR AI*' } | Select-Object -First 1
if (-not $cert) {
    $cert = New-SelfSignedCertificate -Subject 'CN=RAPR AI' -Type CodeSigningCert -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(5)
    Write-Host "  Certificate created: $($cert.Thumbprint)"
} else {
    Write-Host "  Certificate already exists, reusing."
}
