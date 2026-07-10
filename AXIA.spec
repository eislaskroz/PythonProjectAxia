# -*- mode: python ; coding: utf-8 -*-
"""Especificación PyInstaller consolidada para AXIA.

La configuración sensible (.env) NO se empaqueta. Debe copiarse junto a
AXIA.exe o colocarse en la carpeta de datos local del usuario.
"""
from PyInstaller.utils.hooks import collect_all


datas = [
    ('assets', 'assets'),
    ('ui/axia_theme.json', 'ui'),
    ('.env.example', '.'),
]
binaries = []
hiddenimports = []

for package in ('reportlab', 'qrcode', 'PIL', 'customtkinter'):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

# Importaciones dinámicas usadas por ReportLab al generar códigos/QR.
hiddenimports += [
    'reportlab.graphics.barcode.code39',
    'reportlab.graphics.barcode.code93',
    'reportlab.graphics.barcode.code128',
    'reportlab.graphics.barcode.usps',
    'reportlab.graphics.barcode.qr',
    'reportlab.graphics.barcode',
    'reportlab.graphics',
    'reportlab.platypus',
    'reportlab.pdfgen',
]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'unittest.test'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AXIA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/SoloAxia.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AXIA',
)
