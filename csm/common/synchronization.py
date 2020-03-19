#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          synchronization.py
 _description:      Synchronization primitives for CSM Agent

 Creation Date:     03/10/2020
 Author:            Dimitry Didenko

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from asyncio import Event
from csm.common.errors import CsmInternalError


class ThreadSafeEvent(Event):
    """Attempt to add thread-safe feature to the asyncio.Event class.

    Standard asyncio.Event class is not thread safe. From other side, threading.Event class is not
    suitable for as asyncio synchronization primitive: class methods is not awaitable objects
    """

    @property
    def _event_loop(self):
        """Method-wrapper to obtain a current event loop"""
        return self._loop  # TODO: maybe it is better to call asyncio.get_event_loop()

    def clear(self):
        self._event_loop.call_soon_threadsafe(super().clear)

    def is_set(self):
        self._event_loop.call_soon_threadsafe(super().is_set)

    def set(self):
        self._event_loop.call_soon_threadsafe(super().set)

    async def wait(self):
        # await a future
        future = asyncio.run_coroutine_threadsafe(super().wait(), self._event_loop)
        future = asyncio.wrap_future(future)
        done, pending = await asyncio.wait({future})
        if not done:
            raise CsmInternalError("Some internal asyncio error during waiting asyncio.Event.wait")
