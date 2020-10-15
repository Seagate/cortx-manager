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

from csm.common.process import SimpleProcess
from cortx.utils.log import Log

class StorageInfo:

    @staticmethod
    def get_dir_usage(dir_path="", unit="K"):
        """
        Method to get disk usage of provided dir_path
        eg: sudo du -BM /var/log
        :params:
        dir_path: Path to find disk usage info :default: "" :type:str
        unit: Unit to define data block : default: "K" :type:str
        :return:
        :type:tuple
        """
        cmd = f"sudo du -B{unit} {dir_path}"
        return StorageInfo.execute_cmd(cmd)

    @staticmethod
    def get_fs_usage(fs="", unit="K"):
        """
        Method to get disk usage of provided filesystem
        eg: df -BM /var/log/elasticsearch
        :params:
        dir_path: Path to find disk usage of filesystem info :default: "" :type:str
        unit: Unit to define data block : default: "K" :type:str
        :return:
        :type:tuple
        """
        cmd = f"df -B{unit} {fs}"
        return StorageInfo.execute_cmd(cmd)

    @staticmethod
    def execute_cmd(cmd=""):
        sp_es = SimpleProcess(cmd)
        Log.debug(f"Running {cmd}")
        res = sp_es.run()
        Log.debug(f"Output: {res[0]}\nError: {res[1]}\nRC: {res[2]}")
        return res
