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

from typing import Any, Dict
from http import HTTPStatus

from csm.core.services.rgw.s3.utils import CsmRgwConfigurationFactory
from cortx.utils.log import Log


class RGWPlugin:

    def __init__(self):
        """
        Initialize RGW plugin
        """
        Log.INFO("RGW Plugin Loaded")
        self._rgw_admin_client = None
        config = CsmRgwConfigurationFactory.get_rgw_connection_config()
        # self._rgw_admin_client = RGWAdminClient(config.admin_access_key, config.admin_secret_key, config.host, config.port)
        self._admin_uid = config.auth_user
        Log.INFO(f"RGW admin uid: {self._admin_uid}")
        self._api_operations = {
            'CREATE_USER': {
                'ENDPOINT': f"/{self._admin_uid}/user",
                'METHOD': "PUT",
                'REQUEST_BODY_SCHEMA': {
                    'uid': 'uid',
                    'display_name': 'display-name',
                    'email': 'email',
                    'key_type': 'key-type',
                    'access_key': 'access-key',
                    'secret_key': 'secret-key',
                    'user_caps': 'user-caps',
                    'generate_key': 'generate-key',
                    'max_buckets': 'max-buckets',
                    'suspended': 'suspended',
                    'tenant': 'tenant'
                }
            }
        }

    def execute(self, operation, **kwargs):
        api_operation = self._api_operations.get(operation)

        request_body = None
        if api_operation['METHOD'] != 'GET':
            request_body = self._build_request(api_operation['REQUEST_BODY_SCHEMA'], **kwargs)

        return self._process(api_operation, request_body)

    def _build_request(self, request_body_schema, **kwargs):
        request_body = dict()
        for key, value in request_body_schema.items():
            if kwargs.get(key, None) is not None:
                request_body[value] = kwargs.get(key, None)
        Log.INFO(f"RGW Plugin - request body: {request_body}")
        return request_body

    def _process(self, api_operation, request_body):
        # (code, body) = self._rgw_admin_client.signed_http_request()
        # if code != HTTPStatus.CREATED:
        #     return self._create_error(code, body)
        # else:
        #     return self._create_response()
        return {}

    def _create_response(self, cls, data: Dict[str, Any], mapping: Dict[str, str]) -> Any:
        """
        Creates an instance of type `cls` and fills its fields according to mapping.
        :param cls: model's class object.
        :param data: dict with values.
        :param mapping: dict that maps data values to model's attributes.
        :returns: an instance of `cls` type
        """

        pass

    def _create_error(self, status: HTTPStatus, body: str) -> Any:
        """
        Converts a body of a failed query into IamError object.

        :param status: HTTP Status code.
        :param body: parsed HTTP response (dict) with the error's decription.
        :returns: instance of error.
        """

        pass