param(
    [Parameter(Mandatory=$true)][string]$PreviousInstaller,
    [switch]$Silent
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $PreviousInstaller)) { throw "No existe el instalador anterior." }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $env:USERPROFILE "Documents\AXIA\rollback_$stamp"
New-Item -ItemType Directory -Force $backupDir | Out-Null
$envFile = Join-Path $env:LOCALAPPDATA "AXIA\.env"
if (Test-Path $envFile) { Copy-Item $envFile $backupDir -Force }
$logs = Join-Path $env:LOCALAPPDATA "AXIA\logs"
if (Test-Path $logs) { Copy-Item $logs $backupDir -Recurse -Force }
$args = if ($Silent) { @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') } else { @() }
Start-Process -FilePath (Resolve-Path $PreviousInstaller) -ArgumentList $args -Wait
if ($LASTEXITCODE -ne 0) { throw "El instalador anterior terminó con error." }
Write-Host "Rollback ejecutado. Respaldo local: $backupDir" -ForegroundColor Green
