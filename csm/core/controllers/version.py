#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          version.py
 Description:       Implementation of product version details views.

 Creation Date:     06/11/2020
 Author:            Ajay Shingare

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from csm.core.controllers.view import CsmView, CsmAuth
from eos.utils.log import Log
from csm.core.blogic import const

@CsmView._app_routes.view("/api/v1/product_version")
@CsmAuth.public
class ProductVersionView(CsmView):
    def __init__(self, request):
        super(ProductVersionView, self).__init__(request)
        self._service = self.request.app[const.PRODUCT_VERSION_SERVICE]
        self._service_dispatch = {}

    """
    GET REST implementation for fetching product version details
    """
    async def get(self):
        Log.debug("Handling product version information fetch request")
        return await self._service.get_current_version()
    