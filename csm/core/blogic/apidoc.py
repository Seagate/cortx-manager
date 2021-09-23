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

from typing import Dict


SWAGGER_DEFAULT_RESPONSE = {
    200: {"description": "Ok, the requested resource"},
    201: {"description": "Ok, created"},
    400: {"description": "Bad request"},
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
    404: {"description": "Not found"},
    422: {"description": "Unprocessable entity"},
    499: {"description": "Call cancelled by client"},
    500: {"description": "Internal server error"},
}


def default_api_response(*http_codes) -> Dict[int, Dict]:
    return {http_code: SWAGGER_DEFAULT_RESPONSE[http_code]
            for http_code in http_codes if http_code in SWAGGER_DEFAULT_RESPONSE}
