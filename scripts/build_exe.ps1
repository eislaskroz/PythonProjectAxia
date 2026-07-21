# AXIA - Compilación reproducible en modo carpeta
# Ejecutar desde la raíz:
# powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\main.py")) {
    throw "Ejecuta este script desde la raíz del proyecto AXIA."
}

Write-Host "[1/5] Validando entorno, sintaxis y estructura..." -ForegroundColor Cyan
python .\tools\diagnostico_entorno.py
python .\tools\auditar_proyecto.py

Write-Host "[2/5] Limpiando build/dist anteriores..." -ForegroundColor Cyan
python .\scripts\limpiar_proyecto.py

Write-Host "[3/5] Instalando dependencias..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt

Write-Host "[4/5] Verificando que no se empaqueten secretos..." -ForegroundColor Cyan
if ((Get-Content .\AXIA.spec -Raw) -match "\.env['\"]") { throw "AXIA.spec intenta empaquetar .env. Compilación cancelada." }
if (Test-Path ".\dist\AXIA\.env") { Remove-Item ".\dist\AXIA\.env" -Force }
Write-Host "Generando AXIA.exe desde AXIA.spec..." -ForegroundColor Cyan
pyinstaller --noconfirm --clean AXIA.spec

Write-Host "[5/5] Preparando configuración de despliegue..." -ForegroundColor Cyan
Copy-Item ".env.example" ".\dist\AXIA\.env.example" -Force

Write-Host "" 
Write-Host "Compilación terminada: dist\AXIA\AXIA.exe" -ForegroundColor Green
Write-Host "No se incluyó .env por seguridad." -ForegroundColor Yellow
Write-Host "Copia manualmente .env junto a AXIA.exe en cada equipo de pruebas." -ForegroundColor Yellow
