# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\副业\\项目\\爬北大法典\\北大法宝爬取分字段写入excel\\北大法宝爬虫不下载附件版GUI.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='北大法宝爬虫',
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
    icon=['D:\\副业\\项目\\爬北大法典\\北大法宝爬取分字段写入excel\\icon.ico'],
)
