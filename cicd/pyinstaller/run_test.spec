# -*- mode: python ; coding: utf-8 -*-
#!/usr/bin/env python3
import sys
import os
import re

product = '<PRODUCT>'
csm_path = '<CSM_PATH>'
test_path = '<CSM_PATH>' + '/test'

import_list = []
for root, directories, filenames in os.walk(test_path):
    for filename in filenames:
        if re.match(r'.*.\.py$', filename) and filename != '__init__.py':
            file = os.path.join(root, filename).rsplit('.', 1)[0]\
                .replace(csm_path + "/", "").replace("/", ".")
            import_list.append('csm.' + file)

block_cipher = None

a = Analysis(['/root/rpm/Repo/csm/dist/tmp/csm/test/run_test.py'],
             pathex=['/root/rpm/Repo/exe'],
             binaries=[],
             datas=[],
             hiddenimports=import_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='run_test',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='run_test')
