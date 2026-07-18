$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "=== AXIA: compilación de aplicación ==="
Write-Host ""

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "No existe el entorno virtual .venv"
}

if (-not (Test-Path ".\AXIA.spec")) {
    throw "No se encontró AXIA.spec"
}

$InnoCompiler = "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"

if (-not (Test-Path $InnoCompiler)) {
    throw "No se encontró Inno Setup 6"
}

Remove-Item -Recurse -Force ".\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\dist" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\release" -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force ".\release" | Out-Null

& ".\.venv\Scripts\python.exe" `
    -m PyInstaller `
    --clean `
    --noconfirm `
    ".\AXIA.spec"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller terminó con errores"
}

if (-not (Test-Path ".\dist\AXIA\AXIA.exe")) {
    throw "No se generó dist\AXIA\AXIA.exe"
}

Write-Host ""
Write-Host "=== AXIA: creación del instalador ==="
Write-Host ""

& $InnoCompiler ".\installer\AXIA.iss"

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup terminó con errores"
}

$Installer = Get-ChildItem ".\release\AXIA_Setup_*.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $Installer) {
    throw "No se encontró el instalador final"
}

Write-Host ""
Write-Host "========================================"
Write-Host "INSTALADOR GENERADO CORRECTAMENTE"
Write-Host $Installer.FullName
Write-Host "========================================"