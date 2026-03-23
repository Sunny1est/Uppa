# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
import sys

# Caminho absoluto para a pasta src
src_path = os.path.abspath('src')

a = Analysis(
    [os.path.join(src_path, 'main.py')],
    pathex=[src_path],
    binaries=[],
    datas=[
        (os.path.join(src_path, 'assets'), 'assets'), 
        (os.path.join(src_path, 'uppa_data.db'), '.') # Incluir banco inicial se existir
    ],
    hiddenimports=[
        'win11toast', 
        'winsound', 
        'PIL', 
        'customtkinter', 
        'matplotlib',
        'numpy',
        'pygame',
        'sqlite3',
        'logging.handlers'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Uppa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # False para não mostrar terminal ("Windowed Mode")
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(src_path, 'assets', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Uppa',
)
