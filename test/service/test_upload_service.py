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
import os
import asyncio
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from csm.test.common import TestFailed, TestProvider, Const
from csm.core.blogic import const
from csm.core.services.file_transfer import FileCache
from csm.core.controllers.file_transfer import FileFieldSchema
from csm.core.controllers.view import CsmView
from cortx.utils.log import Log

from aiohttp import web, ClientSession, FormData
from marshmallow import Schema, fields, validate, exceptions


#################
# Tests
#################

test_file_data = b'test_binary_data'
test_tmp_dir = '/tmp/csm/test/file_transfer'


class TestFileUploadSchema(Schema):
    file = fields.Nested(FileFieldSchema())


async def upload_test(request: web.Request):
    """
    Handler function for upload request
    """
    # Create cache dir
    os.system(f"mkdir -p {test_tmp_dir}")

    with FileCache() as cache:
        # Place test dir as FileCache's cache_dir
        cache.cache_dir = test_tmp_dir

        # No files cached
        assert len(cache.files_uuids) == 0

        # CsmView instance for parsing multipart request
        csm_view = CsmView(request)
        parsed_multipart = await csm_view.parse_multipart_request(request, cache)

        # 1 file cached after parsing and it exists
        assert len(cache.files_uuids) == 1
        assert os.path.exists(test_tmp_dir + '/' + str(cache.files_uuids[0]))

        # Validate parse request
        multipart_data = TestFileUploadSchema().load(parsed_multipart)

        # Filename passed correctly
        filename = multipart_data['file']['filename']
        assert filename == 'file.example'

        # Saving file to whatever we want (test dir in this case)
        file_ref = multipart_data['file']['file_ref']
        file_ref.save_file(test_tmp_dir, 'test_file')

    # After we left FileCache context, temporary file doesn't exist anymore
    assert not os.path.exists(test_tmp_dir + '/' + str(cache.files_uuids[0]))

    # Saved file exists and it's data written correctly
    target_file_path = test_tmp_dir + '/' + 'test_file'
    assert os.path.exists(target_file_path)
    with open(target_file_path, 'r') as f:
        output = f.read()
        assert output == test_file_data.decode()

    # Clearing tmp dir and returning success
    shutil.rmtree(test_tmp_dir)
    return web.Response(text='success')


async def send_multipart_request(url):
    """
    Client aiohttp code for sending request
    """
    data = FormData()
    data.add_field('file',
                   test_file_data,
                   filename='file.example',
                   content_type='application/octet-stream')
    async with ClientSession() as session:
        return await session.post(url, data=data)


def test_file_uploading(args):
    """
    Test for checking correctness of upload process
    """

    loop = asyncio.get_event_loop()

    # Clearing test file_cache folder
    if os.path.exists(test_tmp_dir):
        shutil.rmtree(test_tmp_dir)

    # Creating server with aiohttp handler and free port
    app = web.Application()
    app.add_routes([web.post('/', upload_test)])
    handler = app.make_handler()
    server = loop.run_until_complete(loop.create_server(handler, '0.0.0.0', 0))

    # Get ip and given port
    ip, port = server.sockets[0].getsockname()

    # Emulate sending request and checking for returned value
    # (means that all asserts are passed)
    resp = loop.run_until_complete(send_multipart_request(
        f'http://{ip}:{port}/'))
    assert loop.run_until_complete(resp.text()) == 'success'

    # Stop server, closing loop
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


def init(args):
    pass


test_list = [test_file_uploading]

if __name__ == '__main__':
    Log.init('test', '.')
    test_file_uploading()
