#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          commands.py
 Description:       Represents RAS Command and arguments to help parsing
                    command line

 Creation Date:     31/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
from json2xml import json2xml
import pprint
from typing import (ClassVar, Dict)

from prettytable import PrettyTable

class RestRequest:
    """Cli Rest Request Class """

    def __init__(self, url: str, session: ClassVar, options: Dict, args: ClassVar,
                 method: str):
        self._method = method
        self._url = url
        self._session = session
        self._args = args
        self._options = options

    async def _get(self) -> str:
        async with self._session.get(self._url, params=self._options) as response:
            return await response.text()

    async def get_request(self) -> str:
        return await getattr(self, f'_{self._method}')()

class RestResponse:
    """CLI Response Display Class"""

    @staticmethod
    def table(data: list, keys: list) -> None:
        table_obj = PrettyTable()
        for header in keys:
            table_obj.add_column(
                header.capitalize().replace("_", " ").replace("-", " "),
                list(map(lambda x: x.get(header, ""), data)))
        sys.stdout.write("{0}".format(table_obj))

    @staticmethod
    def xml(data):
        sys.stdout.write(json2xml.Json2xml(data).to_xml())

    @staticmethod
    def json(data):
        pprint.pprint(data, indent=4)

    @staticmethod
    def error(rc: int, message: str) -> None:
        sys.stdout.write(f'error({rc}): {message}')

