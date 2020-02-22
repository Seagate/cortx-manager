# -*- mode: python ; coding: utf-8 -*-
#!/usr/bin/env python3
import sys
import os
import re

def import_list(csm_path, walk_path):
    import_list = []
    for root, directories, filenames in os.walk(walk_path):
        for filename in filenames:
            if re.match(r'.*.\.py$', filename) and filename != '__init__.py':
                file = os.path.join(root, filename).rsplit('.', 1)[0]\
                    .replace(csm_path + "/", "").replace("/", ".")
                import_list.append('csm.' + file)
    return import_list

product = '<PRODUCT>'
csm_path = '<CSM_PATH>'
product_path = '<CSM_PATH>' + '/' + product
test_path = '<CSM_PATH>' + '/test'
product_module_list = import_list(csm_path, product_path)
product_module_list.append("csm.cli.support_bundle")
test_module_list = import_list(csm_path, test_path)
test_module_list.remove('csm.test.csm_test')

block_cipher = None

# Analysis
csm_agent = Analysis([csm_path + '/core/agent/csm_agent.py'],
             pathex=[csm_path + '/dist/csm'],
             binaries=[],
             datas=[],
             hiddenimports=product_module_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

csmcli = Analysis([csm_path + '/cli/csmcli.py'],
             pathex=[csm_path + '/dist/csm'],
             binaries=[],
             datas=[],
             hiddenimports=product_module_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

csm_setup = Analysis([csm_path + '/conf/csm_setup.py'],
             pathex=[csm_path + '/dist/csm'],
             binaries=[],
             datas=[],
             hiddenimports=product_module_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

csm_test = Analysis([csm_path + '/test/csm_test.py'],
             pathex=[csm_path + '/dist/csm'],
             binaries=[],
             datas=[],
             hiddenimports=test_module_list,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (csm_agent, 'csm_agent', 'csm_agent'),
       (csmcli, 'csmcli', 'csmcli'),
       (csm_setup, 'csm_setup', 'csm_setup'),
       (csm_test, 'csm_test', 'csm_test') )

# csm_agent
csm_agent_pyz = PYZ(csm_agent.pure, csm_agent.zipped_data,
             cipher=block_cipher)

csm_agent_exe = EXE(csm_agent_pyz,
          csm_agent.scripts,
          [],
          exclude_binaries=True,
          name='csm_agent',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

# csmcli
csmcli_pyz = PYZ(csmcli.pure, csmcli.zipped_data,
             cipher=block_cipher)

csmcli_exe = EXE(csmcli_pyz,
          csmcli.scripts,
          [],
          exclude_binaries=True,
          name='csmcli',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

# csm_setup
csm_setup_pyz = PYZ(csm_setup.pure, csm_setup.zipped_data,
             cipher=block_cipher)

csm_setup_exe = EXE(csm_setup_pyz,
          csm_setup.scripts,
          [],
          exclude_binaries=True,
          name='csm_setup',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

# csm_test
csm_test_pyz = PYZ(csm_test.pure, csm_test.zipped_data,
             cipher=block_cipher)

csm_test_exe = EXE(csm_test_pyz,
          csm_test.scripts,
          [],
          exclude_binaries=True,
          name='csm_test',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(
               # Csm agent
               csm_agent_exe,
               csm_agent.binaries,
               csm_agent.zipfiles,
               csm_agent.datas,

               # csmcli
               csmcli_exe,
               csmcli.binaries,
               csmcli.zipfiles,
               csmcli.datas,

               # csm_setup
               csm_setup_exe,
               csm_setup.binaries,
               csm_setup.zipfiles,
               csm_setup.datas,

               # csm_test
               csm_test_exe,
               csm_test.binaries,
               csm_test.zipfiles,
               csm_test.datas,

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
