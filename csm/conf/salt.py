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
    def get_salt_data(method, key):
        try:
            process = SimpleProcess(f"salt-call {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            Log.logger.warn(f"Error in command execution : {e}")
        if stderr:
            Log.logger.warn(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result['local']

    @staticmethod
    def get_salt_data_with_exception(method, key):
        try:
            process = SimpleProcess(f"salt-call {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            raise PillarDataFetchError(f"Error in command execution : {e}")
        if stderr:
            raise PillarDataFetchError(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result['local']

    @staticmethod
    def get_salt_data_using_minion_id(minion_id, method, key):
        try:
            process = SimpleProcess(f"salt {minion_id} {method} {key} --out=json")
            stdout, stderr, rc = process.run()
        except Exception as e:
            raise PillarDataFetchError(f"Error in command execution : {e}")
        if stderr:
            raise PillarDataFetchError(stderr)
        res = stdout.decode('utf-8')
        if rc == 0 and res != "":
            result = json.loads(res)
            return result[minion_id]
