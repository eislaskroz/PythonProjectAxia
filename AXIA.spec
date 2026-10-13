# -*- mode: python ; coding: utf-8 -*-
import shutil
import tkinter
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# SECURITY: .env, logs and runtime data must never be bundled.
datas = [('assets', 'assets'), ('ui/axia_theme.json', 'ui')]

# Python 3.14 embeds Tcl/Tk scripts in zipfs, which PyInstaller cannot collect
# as filesystem directories. Extract them to its expected runtime-hook paths.
tk = tkinter.Tk()
tk.withdraw()
tcl_library = tk.tk.eval('info library')
tk_library = tk.tk.getvar('tk_library')
tk.destroy()

tcl_tk_data = Path('build/axia_tcl_data')
if tcl_tk_data.exists():
    shutil.rmtree(tcl_tk_data)
tcl_data = tcl_tk_data / '_tcl_data'
tk_data = tcl_tk_data / '_tk_data'
tcl_tk_data.mkdir(parents=True)
tcl = tkinter.Tcl()
tcl.call('file', 'copy', '-force', tcl_library, str(tcl_data))
tcl.call('file', 'copy', '-force', tk_library, str(tk_data))
for source_root, target_root in ((tcl_data, Path('_tcl_data')), (tk_data, Path('_tk_data'))):
    datas.extend(
        (str(path), str(target_root / path.relative_to(source_root).parent))
        for path in source_root.rglob('*')
        if path.is_file()
    )

binaries = []
hiddenimports = ['reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.code93', 'reportlab.graphics.barcode.code128', 'reportlab.graphics.barcode', 'reportlab.graphics', 'reportlab.platypus', 'reportlab.pdfgen', 'reportlab']
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=False,
    console=False,
    icon="assets/SoloAxia.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AXIA',
)
