#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          observer.py
 _description:      Generic observer pattern implementation

 Creation Date:     01/16/2020
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
import inspect
from typing import Callable


class Observable:
    def __init__(self):
        self._observers = set()

    def add_listener(self, observer: Callable):
        self._observers.add(observer)

    def remove_listener(self, observer: Callable):
        self._observers.discard(observer)

    def _notify_listeners(self, *args, loop, **kwargs):
        for observer in self._observers:
            if inspect.iscoroutinefunction(observer):
                asyncio.run_coroutine_threadsafe(observer(*args, **kwargs), loop=loop)
            else:
                observer(*args, **kwargs)
