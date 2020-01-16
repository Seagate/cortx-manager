#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          view.py
 Description:       Common base view

 Creation Date:     10/16/2019
 Author:            Naval Patel

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json
from aiohttp import web
from csm.core.services.permissions import Permissions

class CsmAuth:
    HDR = 'Authorization'
    TYPE = 'Bearer'
    UNAUTH = { 'WWW-Authenticate': TYPE }
    ATTR_PUBLIC = '_csm_auth_public_'
    ATTR_PERMISSIONS = '_csm_auth_permissions_'

    @classmethod
    def public(cls, handler):
        setattr(handler, cls.ATTR_PUBLIC, True)
        return handler

    @classmethod
    def is_public(cls, handler):
        return getattr(handler, cls.ATTR_PUBLIC, False)

    @classmethod
    def permissions(cls, permissions):
        if not issubclass(type(permissions), Permissions):
            permissions = Permissions(permissions)
        def decorator(handler):
            setattr(handler, cls.ATTR_PERMISSIONS, permissions)
            return handler
        return decorator

    @classmethod
    def get_permissions(cls, handler):
        return getattr(handler, cls.ATTR_PERMISSIONS, Permissions())


class CsmResponse(web.Response):
    def __init__(self, res={}, status=200, headers=None,
                 content_type='application/json',
                 **kwargs):
        body = json.dumps(res)
        super().__init__(body=body, status=status, headers=headers,
                         content_type=content_type, **kwargs)


class CsmView(web.View):

    # derived class will provide service amd service_disatch  details
    _service = None
    _service_dispatch = {}

    # common routes to used by subclass
    _app_routes = web.RouteTableDef()

    def __init__(self, request):
        super(CsmView, self).__init__(request)

    @classmethod
    def route(cls, name):
        return cls._app_routes.view(name)

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
