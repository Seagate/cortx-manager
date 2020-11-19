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

import asyncio
import json
import errno
from copy import deepcopy
from typing import List
from csm.common.process import SimpleProcess
import xmltodict
from csm.cli.support_bundle.support_bundle import SupportBundle
from csm.core.providers.providers import Response


class UpdateCSM:

    @staticmethod
    async def get_pcs_status(component_names: List, group_name: List):
        """
        Check PCS Status for Provided List of Components.
        :param component_names:
        :param group_name:
        :return:
        """
        proc = SimpleProcess("pcs status xml")
        _output, _err, _returncode = proc.run()
        if _returncode != 0:
            raise Exception(f"Pcs Status Command Failed With Error {_err}")
        op = json.loads(json.dumps(xmltodict.parse(_output)))
        groups = op.get("crm_mon", {}).get("resources", {}).get("group", [])
        resource_info = []
        for each_group in groups:
            if each_group.get("@id") in group_name:
                for each_resource in each_group.get('resource'):
                    if each_resource.get("@id") in component_names:
                        resource_info.append(deepcopy(each_resource))
                break
        else:
            raise Exception("Group Not Found in PCS Status.")
        return resource_info

    @staticmethod
    async def ban_resource(resource_id, non_running_node):
        """
        Ban resources on Non Running Node.
        :param resource_id:
        :param running_node:
        :return:
        """

        proc = SimpleProcess(f"pcs resource ban {resource_id} {non_running_node}")
        _output, _err, _returncode = proc.run()
        if _returncode != 0:
            raise Exception(f"Pcs Status Command Failed With Error {_err}")

    @staticmethod
    async def connect_and_update(resource_id, non_running_node):
        provisioner = SupportBundle.import_provisioner_plugin()
        if not provisioner:
            return Response(output="Provisioner package not found.",
                            rc=str(errno.ENOENT))
        provisioner.execute_cortxcli_commands(f"update_csm {resource_id}", non_running_node)

    @staticmethod
    async def clear_resource():
        proc = SimpleProcess(f"pcs resource clear")
        _output, _err, _returncode = proc.run()
        if _returncode != 0:
            raise Exception(f"Pcs clear Command Failed With Error {_err}")

    @staticmethod
    async def move_resource(resource_id, non_running_node):
        """

        :param resource_id:
        :param non_running_node:
        :return:
        """
        proc = SimpleProcess(f"pcs resource move {resource_id} {non_running_node}")
        _output, _err, _returncode = proc.run()
        if _returncode != 0:
            raise Exception(f"Pcs clear Command Failed With Error {_err}")

    @staticmethod
    async def add_update_status(resource_id, non_running_node):
        # Todo: Update status in Consul for Node and Resource ID.
        pass

    @staticmethod
    async def rpm_update(command):
        """

        :param command:
        :return:
        """
        resource_id = command.options.get("resource_id")
        file_path = f"/opt/seagate/cortx/updates/cortx-{resource_id}*"
        commands = ["csm_setup reset --hard",
                    f"rpm -i -U --force {file_path}",
                    "csm_setup post_install",
                    "csm_setup config",
                    "csm_setup init"]
        for each_command in commands:
            proc = SimpleProcess(each_command)
            _output, _err, _returncode = proc.run()
            if _returncode != 0:
                raise Exception(f"Command Failed With Error {_err}")

    @staticmethod
    async def begin_update(command=None):
        """
        Begin Update for CSM.
        :return:
        """

        # Get Current Status of Resource From PCS.
        resource_info = await UpdateCSM.get_pcs_status(['csm-web', 'csm-agent'], ['csm-kibana'])
        # Ban Resources to Run on the current Non-running Nodes.
        for each_resource in resource_info:
            running_node = each_resource.get("node").get("@name")
            resource_id = each_resource.get("@id")
            node_list = ['srvnode_1', 'srvnode_2']
            if running_node not in node_list:
                raise Exception("Invalid Node.")
            non_running_node = (set(node_list).difference({running_node})).pop()
            await UpdateCSM.ban_resource(resource_id, non_running_node)
            await UpdateCSM.connect_and_update(resource_id.replace('-', '_'), non_running_node)
            await UpdateCSM.clear_resource()
            await UpdateCSM.move_resource(resource_id, non_running_node)
            await UpdateCSM.add_update_status(resource_id, non_running_node)


if __name__ == '__main__':
    _loop = asyncio.get_event_loop()
    _loop.run_until_complete(UpdateCSM.begin_update())
