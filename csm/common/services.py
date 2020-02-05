#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          services.py
 Description:       Contains shared logic for services implementation

 Creation Date:     09/11/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import asyncio

class Service:
    def __init__(self):
        super().__init__()
        self._loop = asyncio.get_event_loop()

    def _run_coroutine(self, coro):
        task = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return task.result()


class ApplicationService(Service):
    """
    A service that is intended to be used by controllers
    """
    def __init_(self):
        super().__init__()
