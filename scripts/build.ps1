param(
    [ValidateSet("test", "app", "installer")]
    [string]$Target = "app",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    & $script:Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python terminó con código $LASTEXITCODE: $Arguments" }
}

$Python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "=== AXIA | Proceso unificado de calidad y compilación ===" -ForegroundColor Cyan
Write-Host "Objetivo: $Target"

if (-not (Test-Path ".\main.py")) { throw "Ejecuta el script desde el proyecto AXIA." }
if (-not (Test-Path ".\AXIA.spec")) { throw "No se encontró AXIA.spec." }
if (Test-Path ".\main.spec") { throw "main.spec está obsoleto. AXIA.spec es la única fuente de compilación." }
if ((Get-Content ".\AXIA.spec" -Raw) -match "['\"]\.env['\"]") {
    throw "AXIA.spec intenta empaquetar .env. Proceso cancelado."
}

if (-not $SkipInstall) {
    Invoke-Python -m pip install -r requirements-dev.txt
}

Write-Host "[1/4] Validación estática y sintaxis..." -ForegroundColor Cyan
Invoke-Python .\tools\validar_calidad.py

Write-Host "[2/4] Pruebas automatizadas..." -ForegroundColor Cyan
Invoke-Python -m pytest

if ($Target -eq "test") {
    Write-Host "Calidad y pruebas completadas." -ForegroundColor Green
    exit 0
}

Write-Host "[3/4] Limpieza y compilación reproducible..." -ForegroundColor Cyan
Invoke-Python .\scripts\limpiar_proyecto.py
Invoke-Python -m PyInstaller --noconfirm --clean .\AXIA.spec

if (-not (Test-Path ".\dist\AXIA\AXIA.exe")) { throw "No se generó dist\AXIA\AXIA.exe" }
if (Test-Path ".\dist\AXIA\.env") { throw "Se encontró un .env dentro de dist. Proceso cancelado." }
Copy-Item ".env.example" ".\dist\AXIA\.env.example" -Force

if ($Target -eq "app") {
    Write-Host "Aplicación generada: dist\AXIA\AXIA.exe" -ForegroundColor Green
    exit 0
}

Write-Host "[4/4] Generación del instalador..." -ForegroundColor Cyan
$Candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
)
$InnoCompiler = $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $InnoCompiler) { throw "No se encontró Inno Setup 6 o 7." }

New-Item -ItemType Directory -Force ".\release" | Out-Null
& $InnoCompiler ".\installer\AXIA.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup terminó con errores." }

$Installer = Get-ChildItem ".\release\AXIA_Setup_*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $Installer) { throw "No se encontró el instalador final." }
Write-Host "Instalador generado: $($Installer.FullName)" -ForegroundColor Green
