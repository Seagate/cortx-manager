# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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


class Utility:
    """
    Helper class for common independent utilities.
    """

    @staticmethod
    def remove_json_key(payload, key):
        """
        Removes a particular key from complex a deserialized json payload.

        Args:
            payload (dict): payload from which particular key should be deleted.
            key (str): key which is to be deleted.

        Returns:
            Modified payload.
        """
        if isinstance(payload, dict):
            return {k: Utility.remove_json_key(v, key) for k, v in payload.items() if k != key}
        elif isinstance(payload, list):
            return [Utility.remove_json_key(element, key) for element in payload]
        else:
            return payload
