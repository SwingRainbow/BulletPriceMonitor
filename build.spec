# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 单文件 exe
用法: pyinstaller build.spec
"""
import os

block_cipher = None
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'run.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'src', 'frontend'), os.path.join('src', 'frontend')),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.edgechromium',
        'bottle',
        'proxy_tools',
        'PIL',
        'src.scraper_worker',
        'src.econ_worker',
        'src.brain_updater',
        'src.price_history',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BulletPriceMonitor',
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
    # icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)
