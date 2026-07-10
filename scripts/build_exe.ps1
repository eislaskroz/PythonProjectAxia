# AXIA - Generación de ejecutable en modo carpeta
# Ejecutar desde la raíz del proyecto:
# powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"

Write-Host "Limpiando build/dist anteriores..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "Instalando dependencias de desarrollo..." -ForegroundColor Cyan
python -m pip install -r requirements-dev.txt

Write-Host "Generando AXIA.exe..." -ForegroundColor Cyan
pyinstaller --noconfirm --clean --onedir --windowed --name AXIA `
  --collect-all reportlab `
  --collect-all PIL `
  --collect-all qrcode `
  --add-data "assets;assets" `
  --add-data "ui\axia_theme.json;ui" `
  --icon "assets\SoloAxia.ico" `
  main.py

Write-Host "Listo. Revisa dist\AXIA\AXIA.exe" -ForegroundColor Green
Write-Host "IMPORTANTE: copia tu archivo .env dentro de dist\AXIA\ antes de probar en otra PC." -ForegroundColor Yellow
