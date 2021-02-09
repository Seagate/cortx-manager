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
cc_path = '<CORTXCLI_PATH>'
plugin_product_dir = 'cortx'
product_path = '<CORTXCLI_PATH>' + '/plugins/' + plugin_product_dir
db_file_path = '<CORTXCLI_PATH>' + '/cli/conf/etc/cli/database_cli.yaml'
product_module_list = import_list(cc_path, product_path)
cli_module_list = import_models(db_file_path)
product_module_list.extend(cli_module_list)
product_module_list.append("csm.cli.support_bundle")
product_module_list.append("csm.cli.scripts")
product_module_list.append("csm.conf")
product_module_list.append("cortx.utils.security.secure_storage")

block_cipher = None

# Analysis
cortxcli = Analysis([cc_path + '/cli/cortxcli.py'],
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

# cortxcli
cortxcli_pyz = PYZ(cortxcli.pure, cortxcli.zipped_data,
             cipher=block_cipher)

cortxcli_exe = EXE(cortxcli_pyz,
          cortxcli.scripts,
          [],
          exclude_binaries=True,
          name='cortxcli',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(
               # cortxcli
               cortxcli_exe,
               cortxcli.binaries,
               cortxcli.zipfiles,
               cortxcli.datas,

               strip=False,
               upx=True,
               upx_exclude=[],
               name='lib')
