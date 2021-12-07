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

import json
import asyncio
from csm.common.errors import InvalidRequest
from cortx.utils.log import Log
from csm.core.services.file_transfer import FileRef, FileCache
from csm.common.errors import CsmInternalError
import os

from aiohttp import web
from csm.core.services.permissions import PermissionSet


class CsmAuth:
    HDR = 'Authorization'
    TYPE = 'Bearer'
    UNAUTH = {'WWW-Authenticate': TYPE}
    ATTR_PUBLIC = '_csm_auth_public_'
    ATTR_HYBRID = '_csm_auth_hybrid_'
    ATTR_PERMISSIONS = '_csm_auth_permissions_'

    @classmethod
    def public(cls, handler):
        setattr(handler, cls.ATTR_PUBLIC, True)
        return handler

    @classmethod
    def hybrid(cls, handler):
        setattr(handler, cls.ATTR_HYBRID, True)
        return handler

    @classmethod
    def is_public(cls, handler):
        return getattr(handler, cls.ATTR_PUBLIC, False)

    @classmethod
    def is_hybrid(cls, handler):
        return getattr(handler, cls.ATTR_HYBRID, False)

    @classmethod
    def permissions(cls, permissions):
        if not issubclass(type(permissions), PermissionSet):
            permissions = PermissionSet(permissions)
        def decorator(handler):
            setattr(handler, cls.ATTR_PERMISSIONS, permissions)
            return handler
        return decorator

    @classmethod
    def get_permissions(cls, handler):
        return getattr(handler, cls.ATTR_PERMISSIONS, PermissionSet())


class CsmResponse(web.Response):
    def __init__(self, res={}, status=200, headers=None,
                 content_type='application/json',
                 **kwargs):
        body = json.dumps(res)
        super().__init__(body=body, status=status, headers=headers,
                         content_type=content_type, **kwargs)


class CsmHttpException(web.HTTPException):
    ''' Temporary solution: Imitate common REST API error structure '''

    def __init__(self, status, error_code, message_id, message, args=None):
        self.status_code = status
        body = {
            "error_code": error_code,
            "message_id": message_id,
            "message":  message,
        }
        if args is not None:
            body["error_format_args"] = args
        json_body = json.dumps(body)
        super().__init__(body=json_body, content_type='application/json')


class CsmView(web.View):

    # derived class will provide service amd service_disatch  details
    _service = None
    _service_dispatch = {}

    # common routes to used by subclass
    _app_routes = web.RouteTableDef()

    def __init__(self, request):
        super(CsmView, self).__init__(request)

    @classmethod
    def is_subclass(cls, handler):
        return issubclass(type(handler), type) and issubclass(handler, cls)

    @classmethod
    def _get_method_handler(cls, handler, name):
        result = None
        if cls.is_subclass(handler):
            result = getattr(handler, name.lower(), None)
        return result

    @classmethod
    def is_public(cls, handler, method):
        ''' Check whether a particular method of the CsmView subclass has
            the 'public' attribute. If not then check whether the handler
            itself has the 'public' attribute '''

        method_handler = cls._get_method_handler(handler, method)
        if method_handler is not None:
            if CsmAuth.is_public(method_handler):
                return True
        return CsmAuth.is_public(handler)

    @classmethod
    def is_hybrid(cls, handler, method):
        ''' Check whether a particular method of the CsmView subclass has
            the 'public' attribute. If not then check whether the handler
            itself has the 'public' attribute '''

        method_handler = cls._get_method_handler(handler, method)
        if method_handler is not None:
            if CsmAuth.is_hybrid(method_handler):
                return True
        return CsmAuth.is_hybrid(handler)

    @classmethod
    def get_permissions(cls, handler, method):
        ''' Obtain the list of required permissions associated with
            the handler. Combine required pesmissions from the individual
            method handler (like get/post/...) and from the whole view '''

        view_permissions = CsmAuth.get_permissions(handler)
        method_handler = cls._get_method_handler(handler, method)
        if method_handler is not None:
            method_permissions = CsmAuth.get_permissions(method_handler)
            # TODO: Merge view and method permissions?
            # permissions = view_permissions | method_permissions
            permissions = method_permissions
        else:
            permissions = view_permissions
        return permissions

    @classmethod
    def asyncio_shield(cls, func):
        def wrapper(*arg, **kw):
            res = asyncio.shield(func(*arg, **kw))
            return res
        return wrapper
    
    def validate_get(self):
        pass

    async def get(self):
        """"
        Generic get call implementation
        """
        self.validate_get()
        if self.request.match_info:
            match_info = {}
            match_info.update(self.request.match_info)
            response_obj = await self._service_dispatch['get_specific'](**match_info)
        else:
            query_parameter = {}
            query_parameter.update(self.request.rel_url.query)
            response_obj = await self._service_dispatch['get'](**query_parameter)
        return response_obj

    async def parse_multipart_request(self,
                                      request,
                                      file_cache: FileCache,
                                      content_byte_size_limit=100 * (1024 ** 2),
                                      file_byte_size_limit=2 * (1024 ** 3)):
        """
        Parse multipart request to dict
        Default limit for non-file content is 100 MB
        Default limit for file content is 2 GB
        """
        Log.debug("Handling file upload request")

        def get_extension(filename):
            parts = filename.split('.')
            return parts[-1] if len(parts) > 1 else ''

        # TODO: make handling in case file_cache is None

        ct = self.request.headers.get('Content-Type')
        if ct is None or 'multipart/form-data;' not in ct:
            raise InvalidRequest('"multipart" header is absent')

        parse_results = {}

        reader = await request.multipart()

        if not os.path.exists(file_cache.cache_dir):
            try:
                original_mask = os.umask(0o007)
                Log.debug(f"original mask: {original_mask}")
                os.makedirs(file_cache.cache_dir)
            except Exception as e:
                Log.debug(f"Can not create directory {e}")
                raise CsmInternalError(f"System error during directory creation for "
                                       f"path='{file_cache.cache_dir}': {e}")
            finally:
                new_mask = os.umask(original_mask)
                Log.debug(f"new mask: {new_mask}")
        else:
            Log.debug(f"Cache dir already exists: {file_cache.cache_dir}")

        while True:
            field = await reader.next()
            if field is None:
                break

            fieldname, filename = self.__parse_multipart_part(field)

            # TODO: Add support for attribute "multiple" (HTML5)
            if fieldname in parse_results:
                raise InvalidRequest(
                    'Repeated fieldname in multipart request. Multiple attribute are not supported for now')

            # If field has filename, write it to cache, else place the content in dict
            parse_result = None
            size = 0
            if filename and file_cache is not None:
                extension = get_extension(filename)
                if len(extension) > 10 or not extension.isalnum():
                    # The extension is unsafe to preserve
                    extension = ''

                file_uuid = file_cache.cache_new_file(extension)
                async for chunk in self.aiohttp_body_getter(field):
                    size += len(chunk)
                    if size > file_byte_size_limit:
                        raise InvalidRequest(
                            f'File "{filename}" is bigger than permissible limit. Max size = {file_byte_size_limit} bytes')
                    file_cache.write_chunck(file_uuid, chunk)
                parse_result = {
                    'content_type': ct,
                    'filename': filename,
                    'file_ref': FileRef(file_uuid, file_cache.cache_dir)
                }
            else:
                content = b''
                async for chunk in self.aiohttp_body_getter(field):
                    if size > content_byte_size_limit:
                        raise InvalidRequest(
                            f'Field "{fieldname}" is bigger than permissible limit. Max size = {content_byte_size_limit} bytes')
                    size += len(chunk)
                    content += chunk
                parse_result = {
                    'content_type': ct,
                    'content': content.decode()
                }

            parse_results[fieldname] = parse_result

        return parse_results

    async def aiohttp_body_getter(self,
                                  body_reader,
                                  chunk_byte_size_limit=10 * (1024 **2)):
        """
        chunk_byte_size_limit was figured out as an optimal value for fast upload
        """
        while True:
            # TODO: do aiohttp decode?
            chunk = await body_reader.read_chunk(chunk_byte_size_limit)
            yield chunk
            if chunk == b'':
                break

    def __parse_multipart_part(self, field):
        # Content-Disposition parse
        cd = field.headers.get('Content-Disposition')
        if not cd:
            raise InvalidRequest(
                'Content-Disposition is absent in one of multipart request parts')

        cd_values = cd.split(';')
        if cd_values[0] != 'form-data':
            raise InvalidRequest('"form-data" is absent in one of multipart request parts')

        # Content-Disposition fieldname parse
        if len(cd_values) < 2 or not cd_values[1]:
            raise InvalidRequest('Fieldname is absent in one of multipart request parts')
        fieldname_pair = cd_values[1].split('=')
        if (len(fieldname_pair) != 2 or
            fieldname_pair[0].strip() != 'name' or
                not fieldname_pair[1]):
            raise InvalidRequest('Incorrect fieldname directive in Content-Disposition header')
        fieldname = fieldname_pair[1].strip('"')

        # Content-Disposition filename parse (optional)
        filename = None
        if len(cd_values) > 2:
            filename_pair = cd_values[2].split('=')
            if (len(filename_pair) != 2 or
                filename_pair[0].strip() != 'filename' or
                    not filename_pair[1]):
                raise InvalidRequest(
                    'Incorrect filename directive in Content-Disposition header')
            filename = filename_pair[1].strip('"')

        # Content-Type parse
        ct = field.headers.get('Content-Type')
        if not ct:
            raise InvalidRequest('Content-Type is absent in one of multipart request parts')

        return fieldname, filename
