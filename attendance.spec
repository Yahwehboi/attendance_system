import os

block_cipher = None

import pyzbar
pyzbar_dir = os.path.dirname(pyzbar.__file__)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[
        (os.path.join(pyzbar_dir, 'libzbar-64.dll'), 'pyzbar'),
    ],
    datas=[
        ('database', 'database'),
        ('modules', 'modules'),
        ('qr_codes', 'qr_codes'),
        ('reports', 'reports'),
    ],
    hiddenimports=[
        'PIL',
        'PIL._imagingtk',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'qrcode',
        'cv2',
        'pyzbar',
        'pyzbar.pyzbar',
        'pyzbar.zbar',
        'openpyxl',
        'werkzeug',
        'werkzeug.security',
        'sqlite3',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AttendanceSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)