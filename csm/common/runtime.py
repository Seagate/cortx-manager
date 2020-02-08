"""
 ****************************************************************************
 Filename:          runtime.py
 Description:       CSM runtime properties

 Creation Date:     01/27/2020
 Author:            Tadeu Bastos

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - : 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from typing import List


class Options:
    """
    A quick-and-dirty implementation that stores CSM runtime options and properties.
    """

    debug = False

    @classmethod
    def parse(cls, args: List[str]) -> None:
        cls.debug = '--debug' in args
