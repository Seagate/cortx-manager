# -*- mode: python ; coding: utf-8 -*-
#!/usr/bin/env python3
import sys
import os
import re
import yaml

def import_list(csm_path, walk_path):
    import_list = []
    for root, directories, filenames in os.walk(walk_path):
        for filename in filenames:
            if re.match(r'.*.\.py$', filename) and filename != '__init__.py':
                file = os.path.join(root, filename).rsplit('.', 1)[0]\
                    .replace(csm_path + "/", "").replace("/", ".")
                import_list.append('csm.' + file)
    return import_list

def import_models(file_name):
    import_list = []
    with open(yaml, 'r') as f:
        db_conf = yaml.safe_load(f)
    for each_model in db_conf.get("models", []):
        import_list.append(each_model.get("import_path"))
    return import_list

product = '<PRODUCT>'
csm_path = '<CSM_PATH>'
product_path = '<CSM_PATH>' + '/' + product
db_file_path = 'CSM_PATH' + '/conf/etc/database.yaml'
product_module_list = import_list(csm_path, product_path)
product_module_list.extend(import_models())
product_module_list.append("csm.cli.support_bundle")

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

csm_cleanup = Analysis([csm_path + '/conf/csm_cleanup.py'],
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

MERGE( (csm_agent, 'csm_agent', 'csm_agent'),
       (csmcli, 'csmcli', 'csmcli'),
       (csm_cleanup, 'csm_cleanup', 'csm_cleanup'),
       (csm_setup, 'csm_setup', 'csm_setup') )

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

# csm_cleanup
csm_cleanup_pyz = PYZ(csm_cleanup.pure, csm_cleanup.zipped_data,
             cipher=block_cipher)

csm_cleanup_exe = EXE(csm_cleanup_pyz,
          csm_cleanup.scripts,
          [],
          exclude_binaries=True,
          name='csm_cleanup',
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

               # csm_cleanup
               csm_cleanup_exe,
               csm_cleanup.binaries,
               csm_cleanup.zipfiles,
               csm_cleanup.datas,

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
