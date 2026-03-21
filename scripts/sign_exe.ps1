$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like '*RAPR AI*' } | Select-Object -First 1
if ($cert) {
    $result = Set-AuthenticodeSignature -FilePath 'web_app.dist\web_app.exe' -Certificate $cert -TimestampServer 'http://timestamp.digicert.com'
    Write-Host "  Signed: $($result.Status)"
} else {
    Write-Host "  WARNING: Certificate not found, skipping signing."
}
