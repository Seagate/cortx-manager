# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

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
    with open(file_name, 'r') as f:
        db_conf = yaml.safe_load(f)
    for each_model in db_conf.get("models", []):
        module_name = each_model.get("import_path")
        import_list.append(module_name.rsplit('.', 1)[0])
    return import_list

product = '<PRODUCT>'
csm_path = '<CSM_PATH>'
plugin_product_dir = 'cortx'
product_path = '<CSM_PATH>' + '/plugins/' + plugin_product_dir
product_module_list = import_list(csm_path, product_path)
product_module_list.append("csm.cli.support_bundle")
product_module_list.append("csm.cli.scripts")
product_module_list.append("csm.conf")
product_module_list.append("cortx.utils.security.secure_storage")
db_file_path = '<CSM_PATH>' + '/conf/etc/csm/database.yaml'
models_list = import_models(db_file_path)
product_module_list.extend(models_list)

block_cipher = None

# Analysis
csm_agent = Analysis([csm_path + '/core/agent/csm_agent.py'],
             pathex=['/usr/lib/python3.6/site-packages/'],
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
             pathex=['/usr/lib/python3.6/site-packages/'],
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
             pathex=['/usr/lib/python3.6/site-packages/'],
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
