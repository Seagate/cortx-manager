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

from json import dumps as json_dumps, loads as json_loads
from http import HTTPStatus
from http.client import HTTPResponse
from typing import Any, Dict, Optional, Tuple
from unittest import TestCase, main as unittest_main, skip
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import string
import random


_AGENT_URL = 'http://localhost:28101'
_DEFAULT_ADMIN_USERNAME = 'cortxadmin'
_DEFAULT_ADMIN_PASSWORD = 'Cortxadmin@123'
_SHUTDOWN_SIGNAL_BODY = {
    "operation": "shutdown_signal",
    "arguments": {}
}


class CSMSession:

    __url: str

    __username: Optional[str] = None

    __password: Optional[str] = None

    __authorization_header: Optional[str] = None

    def __init__(
        self, url: str, username: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        self.__url = url
        if username is not None and password is not None:
            self.__username = str(username)
            self.__password = str(password)
        elif username is not None:
            raise ValueError('the password must be provided')
        elif password is not None:
            raise ValueError('the username must be provided')
        assert (
            self.__username is None and self.__password is None or
                self.__username is not None and self.__password is not None
        )

    def __enter__(self):
        if self.__username is not None:
            self.__authorization_header = self.__login(self.__username, self.__password)
        assert self.__authorization_header is not None
        return self

    def __exit__(self, type, value, traceback):
        if self.__username is not None and self.__authorization_header is not None:
            self.__logout(self.__username)

    def __generate_post_content(
        self, body: Any, headers: Optional[Dict[str, str]] = None
    ) -> Tuple[Any, Dict[str, str]]:
        if headers is None:
            headers = {}
        if isinstance(body, dict):
            body = json_dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        elif body is not None:
            raise TypeError('unsupported body type')
        if headers.get('Authorization') is None and self.__authorization_header is not None:
            headers['Authorization'] = self.__authorization_header
        return body, headers

    def open_endpoint(
        self,
        method: str,
        endpoint: str,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> HTTPResponse:
        url = f'{self.__url}/{endpoint}'
        data, headers = self.__generate_post_content(body)
        request = Request(url, method=method, data=data, headers=headers)
        response = urlopen(request)
        assert isinstance(response, HTTPResponse)
        return response

    def __login(self, username: str, password: str) -> str:
        body = {
            'username': username,
            'password': password,
        }
        resp = self.open_endpoint('POST', 'api/v2/login', body)
        return resp.headers['Authorization']


    def __logout(self, username: str) -> None:
        resp = self.open_endpoint('POST', 'api/v2/logout')

    @property
    def username(self):
        return self.__username


def _body_as_object(resp: HTTPResponse) -> Any:
    body = resp.read()
    return json_loads(body)


class TestUserManagementAPIFunctionalRequirements(TestCase):

    __created_users = []


    @classmethod
    def tearDownClass(cls):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            for user in cls.__created_users:
                session.open_endpoint('DELETE', f'api/v2/csm/users/{user}')

    def test_000_default_admin_user_exists(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            return

    def test_010__PREPARE(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            # create required admin user
            username = 'test_admin0'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create required manage users
            username = 'test_manage0'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create required monitor users
            username = 'test_monitor0'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_shutdown_signal_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            resp = session.open_endpoint(
                'POST', 'api/v2/system/management/cluster', _SHUTDOWN_SIGNAL_BODY)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_shutdown_signal_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            session.open_endpoint('POST', 'api/v2/system/management/cluster', _SHUTDOWN_SIGNAL_BODY)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_shutdown_signal_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            session.open_endpoint(
                'POST', 'api/v2/system/management/cluster', _SHUTDOWN_SIGNAL_BODY)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)


if __name__ == '__main__':
    unittest_main()
