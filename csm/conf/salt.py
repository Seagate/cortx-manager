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

from cortx.utils.log import Log
from csm.common.errors import InvalidRequest
from csm.common.process import SimpleProcess

import json


class PillarDataFetchError(InvalidRequest):
    pass


class SaltWrappers:
    @staticmethod
    def get_salt_call(method, key, on_salt_error='raise'):
        if on_salt_error not in ('raise', 'log'):
            raise ValueError(f'Invalid argument: on_salt_error={on_salt_error}')
        try:
            process = SimpleProcess(f"salt-call {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            desc = f'Error in command execution : {e}'
            if on_salt_error == 'raise':
                raise PillarDataFetchError(desc)
            Log.logger.warn(desc)
        if stderr:
            if on_salt_error == 'raise':
                raise PillarDataFetchError(stderr)
            Log.logger.warn(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result['local']

    @staticmethod
    def get_salt(method, key, minion_id=None, on_salt_error='raise'):
        if on_salt_error not in ('raise', 'log'):
            raise ValueError(f'Invalid argument: on_salt_error={on_salt_error}')
        try:
            minion_arg = '*' if minion_id is None else minion_id
            cmd = f'salt {minion_arg} {method} {key} --out=json --static'
            process = SimpleProcess(cmd)
            stdout, stderr, rc = process.run()
        except Exception as e:
            desc = f'Error in command execution : {e}'
            if on_salt_error == 'raise':
                raise PillarDataFetchError(desc)
            Log.logger.warn(desc)
        if stderr:
            if on_salt_error == 'raise':
                raise PillarDataFetchError(stderr)
            Log.logger.warn(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result if minion_id is None else result[minion_id]
