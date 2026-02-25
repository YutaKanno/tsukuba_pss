# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('main_page.py', '.'), ('member.py', '.'), ('plate.py', '.'), ('field.py', '.'), ('cal_stats.py', '.'), ('config.py', '.'), ('db', 'db'), ('assets/Field3.png', 'assets'), ('assets/Plate_L.png', 'assets'), ('assets/Plate_R.png', 'assets'), ('assets/tsukuba_logo.png', 'assets'), ('assets/icon.ico', 'assets'), ('fonts/ipaexg.ttf', 'fonts'), ('fonts/ipaexm.ttf', 'fonts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Yuta\\Desktop\\PyFile2024\\stm_tsukubax\\icon.ico'],
)
