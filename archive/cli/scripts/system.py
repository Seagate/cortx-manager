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
from csm.core.blogic import const
from csm.common.process import AsyncioSubprocess
from cortx.utils.log import Log
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.core.providers.providers import Response

class System:

    @staticmethod
    async def unmaintenance(command):
        """
        Wrapper method for HCTL commands.
        :param command: Command object from argparser.
        :return:
        """

        _command = "start"

        Log.debug(f"executing command :-  "
                  f"{const.CORTXHA_CLUSTER.format(command=_command)}")

        _unstandby_cmd = const.CORTXHA_CLUSTER.format(command=_command)
        subprocess_obj = AsyncioSubprocess(_unstandby_cmd)
        _output, _err, _rc = await subprocess_obj.run()
        if _rc != 0:
            Log.error(f"_output={_output}\n _err={_err}")
            sys.stderr.write(const.HCTL_ERR_MSG)
            return
        return Response(output = "Starting System ...", rc=CSM_OPERATION_SUCESSFUL)
