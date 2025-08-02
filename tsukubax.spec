# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['tsukubax.py'],
    pathex=[],
    binaries=[],
    datas=[('main_page.py', '.'), ('member.py', '.'), ('plate.py', '.'), ('field.py', '.'), ('cal_stats.py', '.'), ('game_data.csv', '.'), ('メンバー登録用.csv', '.'), ('member_remember.csv', '.'), ('Field3.png', '.'), ('Plate_L.png', '.'), ('Plate_R.png', '.'), ('ipaexg.ttf', '.'), ('ipaexm.ttf', '.')],
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
    name='tsukubax',
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
