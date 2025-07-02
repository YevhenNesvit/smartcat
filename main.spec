# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

# Автоматично знаходимо всі Python файли в проекті
def collect_all_modules():
    modules = []
    for root, dirs, files in os.walk('.'):
        # Пропускаємо системні папки
        if any(skip in root for skip in ['.git', '__pycache__', 'build', 'dist']):
            continue
        
        for file in files:
            if file.endswith('.py') and file != 'main.py':
                rel_path = os.path.relpath(os.path.join(root, file))
                module_path = rel_path.replace(os.sep, '.').replace('.py', '')
                if module_path.startswith('.'):
                    module_path = module_path[1:]
                modules.append(module_path)
    return modules

# Збираємо всі модулі
all_modules = collect_all_modules()

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyQt5 модулі
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        # Ваші модулі
        'workers',
        'workers.file_worker',
        'gui',
        'gui.main_window',
    ] + all_modules,  # Додаємо всі знайдені модулі
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
    name='SmartCAT',
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
)