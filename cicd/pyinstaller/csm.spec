# -*- mode: python ; coding: utf-8 -*-

csm_path = '<CSM_PATH>'

block_cipher = None

# Analysis
csm_agent = Analysis([csm_path + '/core/agent/csm_agent.py'],
             pathex=[csm_path + '/dist/csm'],
             binaries=[],
             datas=[],
             hiddenimports=[],
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
             hiddenimports=[],
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
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

MERGE( (csm_agent, 'csm_agent', 'csm_agent'),
       (csmcli, 'csmcli', 'csmcli'),
       (csm_setup, 'csm_setup', 'csm_setup'))

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

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
