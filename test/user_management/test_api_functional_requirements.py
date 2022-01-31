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

import ssl
from json import dumps as json_dumps, loads as json_loads
from http import HTTPStatus
from http.client import HTTPResponse
from typing import Any, Dict, List, Optional, Tuple
from unittest import TestCase, main as unittest_main
from urllib.error import HTTPError
from urllib.request import Request, urlopen


_AGENT_URL = 'https://localhost:8081'
_DEFAULT_ADMIN_USERNAME = 'cortxadmin'
_DEFAULT_ADMIN_PASSWORD = 'Cortxadmin@123'


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
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = f'{self.__url}/{endpoint}'
        data, headers = self.__generate_post_content(body)
        request = Request(url, method=method, data=data, headers=headers)
        response = urlopen(request, context=ctx)
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
        self.open_endpoint('POST', 'api/v2/logout')

    @property
    def username(self):
        return self.__username


def _body_as_object(resp: HTTPResponse) -> Any:
    body = resp.read()
    return json_loads(body)


class TestUserManagementAPIFunctionalRequirements(TestCase):

    __created_users: List[str] = []

    @classmethod
    def tearDownClass(cls):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            for user in cls.__created_users:
                session.open_endpoint('DELETE', f'api/v2/csm/users/{user}')

    def test_000_default_admin_user_exists(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD):
            pass

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
            username = 'test_manage1'
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
            username = 'test_monitor1'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_create_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_admin_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_create_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_manage_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_create_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_monitor_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_create_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_by_manage'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            session.open_endpoint('POST', 'api/v2/csm/users', new_user)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_create_manage_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_manage_by_manage'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_create_monitor_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_monitor_by_manage'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_010_create_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_by_monitor'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            session.open_endpoint('POST', 'api/v2/csm/users', new_user)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_create_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage_by_monitor'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            session.open_endpoint('POST', 'api/v2/csm/users', new_user)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_create_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor_by_monitor'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            session.open_endpoint('POST', 'api/v2/csm/users', new_user)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_change_email_of_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_admin0'
            new_email = {
                'email': f'{username}_by_admin@cortx-examples.seagate.com',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_manage1'
            new_email = {
                'email': f'{username}_by_admin@cortx-examples.seagate.com',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_monitor1'
            new_email = {
                'email': f'{username}_by_admin@cortx-examples.seagate.com',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_self_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_admin0', 'Seagate@1') as session:
            username = session.username
            new_email = {
                'email': f'{username}_by_self@cortx-examples.seagate.com',
                'current_password': 'Seagate@1',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
            self.assertRaises(HTTPError) as cm:
                username = 'test_admin0'
                new_email = {
                    'email': f'{username}_by_manage@cortx-examples.seagate.com',
                }
                session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_change_email_of_manage_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_manage1'
            new_email = {
                'email': f'{username}_by_manage@cortx-examples.seagate.com',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_monitor_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_monitor1'
            new_email = {
                'email': f'{username}_by_manage@cortx-examples.seagate.com',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_self_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = session.username
            new_email = {
                'email': f'{username}_by_self@cortx-examples.seagate.com',
                'current_password': 'Seagate@1',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_change_email_of_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin0'
            new_email = {
                'email': f'{username}_by_monitor@cortx-examples.seagate.com',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_change_email_of_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage1'
            new_email = {
                'email': f'{username}_by_monitor@cortx-examples.seagate.com',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_change_email_of_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor1'
            new_email = {
                'email': f'{username}_by_monitor@cortx-examples.seagate.com',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_010_change_email_of_self_as_monitor_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session:
            username = session.username
            new_email = {
                'email': f'{username}_by_self@cortx-examples.seagate.com',
                'current_password': 'Seagate@1',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_email)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_010_search_existing_user_by_name_ok(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session:
            username = 'cortxadmin'
            resp = session.open_endpoint('GET', f'api/v2/csm/users?username={username}')
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)
            body = _body_as_object(resp)
            usernames = [user['username'] for user in body['users']]
            self.assertTrue(username in usernames)

    def test_014_change_password_of_self_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_admin0', 'Seagate@1') as session:
            username = session.username
            new_password = {
                'current_password': 'Seagate@1',
                'password': 'Seagate@99',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_014_change_password_of_self_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage1', 'Seagate@1') as session:
            username = session.username
            new_password = {
                'current_password': 'Seagate@1',
                'password': 'Seagate@99',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_014_change_password_of_self_as_monitor_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_monitor1', 'Seagate@1') as session:
            username = session.username
            new_password = {
                'current_password': 'Seagate@1',
                'password': 'Seagate@99',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_015_reset_admin_user_password_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_admin0'
            new_password = {
                'password': 'Seagate@2',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_015_reset_manage_user_password_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_manage1'
            new_password = {
                'password': 'Seagate@2',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_015_reset_monitor_user_password_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_monitor1'
            new_password = {
                'password': 'Seagate@2',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_015_reset_admin_user_password_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin0'
            new_password = {
                'password': 'Seagate@3',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_015_reset_manage_user_password_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_manage1'
            new_password = {
                'password': 'Seagate@3',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_015_reset_monitor_user_password_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_monitor1'
            new_password = {
                'password': 'Seagate@3',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_015_reset_admin_user_password_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin0'
            new_password = {
                'password': 'Seagate@4',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_015_reset_manage_user_password_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage1'
            new_password = {
                'password': 'Seagate@4',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_015_reset_monitor_user_password_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor1'
            new_password = {
                'password': 'Seagate@4',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_password)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020__PREPARE(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            # create admin user to be deleted by admin
            username = 'test_admin_del_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            # create manage user to be deleted by admin
            username = 'test_manage_del_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            # create monitor user to be deleted by admin
            username = 'test_monitor_del_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            # create admin user to be deleted by itself
            username = 'test_admin_del_by_itself'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            # create manage user to be deleted by itself
            username = 'test_manage_del_by_itself'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            # create monitor user to be deleted by itself
            username = 'test_monitor_del_by_itself'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)

    def test_020_delete_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_admin_del_by_admin'
            resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_020_delete_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_manage_del_by_admin'
            resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_020_delete_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_monitor_del_by_admin'
            resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_020_delete_itself_as_one_of_existing_admin_users_ok(self):
        resp = None
        with self.assertRaises(HTTPError) as cm, \
                CSMSession(_AGENT_URL, 'test_admin_del_by_itself', 'Seagate@1') as session:
            username = session.username
            resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.UNAUTHORIZED)
        self.assertIsInstance(resp, HTTPResponse)
        self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_020_delete_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin0'
            session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020_delete_manage_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage1'
            session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020_delete_monitor_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor1'
            session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020_delete_itself_as_manage_user_ok(self):
        resp = None
        with self.assertRaises(HTTPError) as cm, \
                CSMSession(_AGENT_URL, 'test_manage_del_by_itself', 'Seagate@1') as session:
            username = session.username
            resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.UNAUTHORIZED)
        self.assertIsInstance(resp, HTTPResponse)
        self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_020_delete_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin0'
            session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020_delete_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage1'
            session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020_delete_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor1'
            session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_020_delete_itself_as_monitor_user_ok(self):
        resp = None
        with self.assertRaises(HTTPError) as cm, \
                CSMSession(_AGENT_URL, 'test_monitor_del_by_itself', 'Seagate@1') as session:
            username = session.username
            resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.UNAUTHORIZED)
        self.assertIsInstance(resp, HTTPResponse)
        self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030__PREPARE(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            # create admin user
            username = 'test_admin_change_role'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create manage user
            username = 'test_manage_change_role'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create monitor user
            username = 'test_monitor_change_role'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'monitor',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create cycle (by admin) user: admin->manage->admin->monitor->manage->monitor->admin
            username = 'test_cycle_change_role_by_admin'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create cycle (by manage) user: manage->monitor->manage
            username = 'test_cycle_change_role_by_manage'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'manage',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create admin->manage (by self) user
            username = 'test_admin_to_manage_role'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)
            # create admin->monitor (by self) user
            username = 'test_admin_to_monitor_role'
            new_user = {
                'username': username,
                'email': f'{username}@cortx-examples.seagate.com',
                'role': 'admin',
                'password': 'Seagate@1',
            }
            resp = session.open_endpoint('POST', 'api/v2/csm/users', new_user)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.CREATED)
            type(self).__created_users.append(username)

    def test_030_change_role_of_admin_user_to_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'admin',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_admin_user_to_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'manage',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_admin_user_to_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'monitor',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_manage_user_to_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage_change_role'
            new_role = {
                'role': 'admin',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_manage_user_to_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage_change_role'
            new_role = {
                'role': 'manage',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_manage_user_to_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage_change_role'
            new_role = {
                'role': 'monitor',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_monitor_user_to_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor_change_role'
            new_role = {
                'role': 'admin',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_monitor_user_to_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor_change_role'
            new_role = {
                'role': 'manage',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_monitor_user_to_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor_change_role'
            new_role = {
                'role': 'monitor',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_self_to_admin_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor_change_role', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = session.username
            new_role = {
                'role': 'admin',
                'current_password': 'Seagate@1',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_self_to_manage_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor_change_role', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = session.username
            new_role = {
                'role': 'manage',
                'current_password': 'Seagate@1',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_self_to_monitor_user_as_monitor_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_monitor_change_role', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = session.username
            new_role = {
                'role': 'monitor',
                'current_password': 'Seagate@1',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_admin_user_to_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'admin',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_admin_user_to_manage_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'manage',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_admin_user_to_monitor_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'monitor',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_manage_user_to_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_manage_change_role'
            new_role = {
                'role': 'admin',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_manage_user_to_manage_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_manage_change_role'
            new_role = {
                'role': 'manage',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_monitor_user_to_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = 'test_monitor_change_role'
            new_role = {
                'role': 'admin',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(HTTPStatus(cm.exception.status)), HTTPStatus.FORBIDDEN)

    def test_031_change_role_of_manage_user_to_monitor_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_cycle_change_role_by_manage'
            new_role = {
                'role': 'monitor',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_032_change_role_of_monitor_user_to_manage_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_cycle_change_role_by_manage'
            new_role = {
                'role': 'manage',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_monitor_user_to_monitor_user_as_manage_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_manage0', 'Seagate@1') as session:
            username = 'test_monitor_change_role'
            new_role = {
                'role': 'monitor',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_self_to_admin_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage_change_role', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = session.username
            new_role = {
                'role': 'admin',
                'current_password': 'Seagate@1',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_self_to_manage_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage_change_role', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = session.username
            new_role = {
                'role': 'manage',
                'current_password': 'Seagate@1',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_self_to_monitor_user_as_manage_user_fail(self):
        with CSMSession(_AGENT_URL, 'test_manage_change_role', 'Seagate@1') as session, \
                self.assertRaises(HTTPError) as cm:
            username = session.username
            new_role = {
                'role': 'monitor',
                'current_password': 'Seagate@1',
            }
            session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
        self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)

    def test_030_change_role_of_admin_user_to_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_admin_change_role'
            new_role = {
                'role': 'admin',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_manage_user_to_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_manage_change_role'
            new_role = {
                'role': 'manage',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_monitor_user_to_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_monitor_change_role'
            new_role = {
                'role': 'monitor',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_self_to_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_admin_change_role', 'Seagate@1') as session:
            username = session.username
            new_role = {
                'role': 'admin',
                'current_password': 'Seagate@1',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_self_to_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_admin_to_manage_role', 'Seagate@1') as session:
            username = session.username
            new_role = {
                'role': 'manage',
                'current_password': 'Seagate@1',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_030_change_role_of_self_to_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, 'test_admin_to_monitor_role', 'Seagate@1') as session:
            username = session.username
            new_role = {
                'role': 'monitor',
                'current_password': 'Seagate@1',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_031_change_role_of_admin_user_to_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_cycle_change_role_by_admin'
            new_role = {
                'role': 'manage',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_032_change_role_of_manage_user_to_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_cycle_change_role_by_admin'
            new_role = {
                'role': 'admin',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_033_change_role_of_admin_user_to_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_cycle_change_role_by_admin'
            new_role = {
                'role': 'monitor',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_034_change_role_of_monitor_user_to_manage_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_cycle_change_role_by_admin'
            new_role = {
                'role': 'manage',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_035_change_role_of_manage_user_to_monitor_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_cycle_change_role_by_admin'
            new_role = {
                'role': 'monitor',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_036_change_role_of_monitor_user_to_admin_user_as_admin_user_ok(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = 'test_cycle_change_role_by_admin'
            new_role = {
                'role': 'admin',
            }
            resp = session.open_endpoint('PATCH', f'api/v2/csm/users/{username}', new_role)
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)

    def test_040__PREPARE(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            resp = session.open_endpoint('GET', 'api/v2/csm/users?role=admin')
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)
            users = _body_as_object(resp).get('users')
            self.assertIsNotNone(users)
            for user in users:
                username = user['username']
                if username == _DEFAULT_ADMIN_USERNAME:
                    continue
                resp = session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
                self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)
                type(self).__created_users.remove(username)

    def test_040_delete_itself_as_single_admin_user_fail(self):
        with CSMSession(_AGENT_URL, _DEFAULT_ADMIN_USERNAME, _DEFAULT_ADMIN_PASSWORD) as session:
            username = session.username
            resp = session.open_endpoint('GET', 'api/v2/csm/users?role=admin')
            self.assertEqual(HTTPStatus(resp.status), HTTPStatus.OK)
            users = _body_as_object(resp).get('users')
            self.assertIsNotNone(users)
            self.assertEqual(len(users), 1)
            user = users[0]
            self.assertEqual(user.get('username'), username)
            with self.assertRaises(HTTPError) as cm:
                session.open_endpoint('DELETE', f'api/v2/csm/users/{username}')
            self.assertEqual(HTTPStatus(cm.exception.status), HTTPStatus.FORBIDDEN)


if __name__ == '__main__':
    unittest_main()
