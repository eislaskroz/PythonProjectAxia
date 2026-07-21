param(
    [Parameter(Mandatory=$true)][string[]]$Files,
    [switch]$RequireSignature
)
$ErrorActionPreference = "Stop"
$thumbprint = $env:AXIA_SIGN_CERT_THUMBPRINT
$timestamp = if ($env:AXIA_TIMESTAMP_URL) { $env:AXIA_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }
$signtool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if (-not $signtool) {
    if ($RequireSignature) { throw "No se encontró signtool.exe (Windows SDK)." }
    Write-Warning "Firma omitida: no se encontró signtool.exe."
    exit 0
}
if (-not $thumbprint) {
    if ($RequireSignature) { throw "Falta AXIA_SIGN_CERT_THUMBPRINT." }
    Write-Warning "Firma omitida: falta AXIA_SIGN_CERT_THUMBPRINT."
    exit 0
}
foreach ($file in $Files) {
    if (-not (Test-Path $file)) { throw "No existe el archivo a firmar: $file" }
    & $signtool sign /sha1 $thumbprint /fd SHA256 /tr $timestamp /td SHA256 $file
    if ($LASTEXITCODE -ne 0) { throw "No fue posible firmar $file" }
    & $signtool verify /pa /v $file
    if ($LASTEXITCODE -ne 0) { throw "La verificación de firma falló: $file" }
}
