"""
 ****************************************************************************
 Filename:          decorators.py
 Description:       A collection of general-purpose decorators and helper functions.

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

from typing import Callable


class Decorators:
    """
    A collection of general-purpose decorators.
    """

    @staticmethod
    def decorate_if(condition: bool, f: Callable) -> Callable:
        """
        Decorates a function according to a condition.

        :param condition: Determines if the decorator is going to be used
        :param f: Decorator to be used in case the condition applies.
        :returns: The decorator ``f`` if ``condition`` is ``True``, the identity function is used as
            a decorator otherwise.
        """

        def identity(f: Callable) -> Callable:
            return f

        if not condition:
            return identity
        return f
