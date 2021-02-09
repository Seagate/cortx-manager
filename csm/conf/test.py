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
from csm.conf.setup import Setup, CsmSetupError
from cortx.utils.log import Log
from csm.core.blogic import const
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL


class Test(Setup):
    def __init__(self):
        super(Test, self).__init__()
        Log.info("Executing Test Cases for CSM.")

    async def execute(self, command):
        """
        Execute CSM Test Command
        :param command: Command Object For CLI. :type: Command
        :return: RC != 0 if Failed else 0 when Passed.
        """
        plan_file = ""
        args_loc = ""
        log_path = ""
        output_file = ""
        if command.options.get("t", ""):
            plan_file = f'-t {command.options.get("t", "")}'
        if command.options.get("f", ""):
            args_loc = f'-f {command.options.get("f", "")}'
        if command.options.get("l", ""):
            log_path = f'-l {command.options.get("l", "")}'
        if command.options.get("o", ""):
            output_file = f'-o {command.options.get("o", "")}'
        command = (f"/usr/bin/csm_test {plan_file} {args_loc} {log_path}"
                   f" {output_file}")
        proc = SimpleProcess(command)
        _output, _err, _return_code = proc.run()
        if _return_code != 0:
            raise CsmSetupError((f"CSM Test Failed \n Output : {_output} \n "
                                 f"Error {_err} \n Return Code {_return_code}"))
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)
