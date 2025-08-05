# -*- mode: python ; coding: utf-8 -*-

# Простий і надійний spec файл
a = Analysis(
    ['main.py'],
    pathex=['.', 'gui', 'services', 'workers'],
    binaries=[],
    datas=[
        ('gui/*', 'gui'),
        ('workers/*', 'workers'),
        ('services/*', 'services'),
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        # Ваші модулі - додаємо конкретний клас
        'workers.text_worker',
        'workers.text_worker.TranslationWorker',
        'workers.file_worker',
        'workers.file_worker.FileTranslationWorker',
        'gui.main_window',
        'gui.main_window.SmartCATGUI',
        'services.document_service',
        'services.document_service.DocumentService',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
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
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
