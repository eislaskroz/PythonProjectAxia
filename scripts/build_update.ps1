param(
    [switch]$SkipInstall,
    [switch]$RequireSignature
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== AXIA | Generar paquete AUTOACTUALIZABLE ===" -ForegroundColor Cyan
Write-Host "Este comando genera el instalador Inno Setup que debe publicarse en act_url." -ForegroundColor Yellow

$argsBuild = @("-Target", "installer")
if ($SkipInstall) { $argsBuild += "-SkipInstall" }
if ($RequireSignature) { $argsBuild += "-RequireSignature" }
& "$PSScriptRoot\build.ps1" @argsBuild
if ($LASTEXITCODE -ne 0) { throw "Falló la compilación de la actualización." }

$Python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
$Version = (& $Python -c "from core.version import APP_VERSION; print(APP_VERSION)").Trim()
$Installer = Resolve-Path ".\release\AXIA_Setup_$Version.exe"
$Hash = (Get-FileHash -Algorithm SHA256 $Installer).Hash.ToLower()

$Info = @"
AXIA $Version - PAQUETE DE ACTUALIZACION

ARCHIVO A PUBLICAR:
$Installer

IMPORTANTE:
- NO publiques dist\\AXIA\\AXIA.exe como actualización.
- Debes publicar AXIA_Setup_$Version.exe completo.
- act_url debe apuntar directamente a ese .exe.

SHA256:
$Hash

Ejemplo de registro Supabase:
update public.db_actualizaciones set act_activa = false where act_canal = 'stable';
insert into public.db_actualizaciones
(act_version, act_url, act_sha256, act_obligatoria, act_notas, act_canal, act_activa)
values
('$Version', 'https://TU-SERVIDOR/AXIA_Setup_$Version.exe', '$Hash', false,
 'Actualización AXIA $Version', 'stable', true);
"@

$InfoPath = ".\release\PUBLICAR_ACTUALIZACION_$Version.txt"
$Info | Set-Content -Path $InfoPath -Encoding UTF8
Write-Host "" 
Write-Host $Info -ForegroundColor Green
Write-Host "Guía guardada en: $InfoPath" -ForegroundColor Cyan
