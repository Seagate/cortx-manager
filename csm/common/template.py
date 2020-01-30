#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          template.py
 _description:      Implementation of templates

 Creation Date:     01/23/2020
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
from .errors import CsmInternalError


class Template:
    """
    Currently this class is just a wrapper over a standard Python's formatting utilities.
    Later it might be modified to support more advanced templating features.
    """
    def __init__(self, raw_template: str):
        self.template = raw_template

    @classmethod
    def from_file(cls, file_name: str):
        try:
            with open(file_name, 'r') as file:
                return cls(file.read())
        except IOError:
            raise CsmInternalError(f'Cannot read from {file_name}') from None

    def render(self, **kwargs):
        return self.template.format(**kwargs)
