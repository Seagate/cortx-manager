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
from eos.utils.log import Log
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
        _user = const.NON_ROOT_USER
        _password = const.NON_ROOT_USER_PASS
        _command = "unmaintenance"

        Log.debug(f"executing command :-  "
                  f"{const.HCTL_NODE.format(command=_command, user=_user, pwd='*****')}")

        _unstandby_cmd = const.HCTL_NODE.format(command=_command, user=_user, pwd=_password)
        subprocess_obj = AsyncioSubprocess(_unstandby_cmd)
        _output, _err = await subprocess_obj.run()
        if _err:
            Log.error(f"_output={_output}\n _err={_err}")
            sys.stderr.write(const.HCTL_ERR_MSG)
            return
        return Response(output = "Starting System ...", rc=CSM_OPERATION_SUCESSFUL)
