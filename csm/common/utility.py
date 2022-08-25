# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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

import time
from functools import wraps

from csm.core.blogic import const
from cortx.utils.conf_store.conf_store import Conf


class Utility:
    """
    Helper class for common independent utilities.
    """

    @staticmethod
    def remove_json_key(payload, key):
        """
        Removes a particular key from complex a deserialized json payload.

        Args:
            payload (dict): payload from which particular key should be deleted.
            key (str): key which is to be deleted.

        Returns:
            Modified payload.
        """
        if isinstance(payload, dict):
            return {k: Utility.remove_json_key(v, key) for k, v in payload.items() if k != key}
        elif isinstance(payload, list):
            return [Utility.remove_json_key(element, key) for element in payload]
        else:
            return payload


class ExponentialBackoff:
    """
    ExponentialBackoff decorator class can decorate a function/method to set a retry logic.

    to its call.It Retries the *calling of decorated function*, using a capped exponential
    backoff.
    Example:
    @ExponentialBackoff(ValueError)
    def foo(x, y=10):
        ...
    or
    @ExponentialBackoff(Exception, tries=2, delay=10, backoff=2, cap=2)
    def bar():
        ...
    Args:
        exception (Exception or tuple(Exception)):  it can be a single exception
                                                    or a tuple of exceptions.
        tries (int): 10     number of times to try before failing.
        delay (int): 1      initiall delay (in seconds) between retries.
        backoff (int): 2    backoff multiplier.
        cap (int): 120      cap for maximum delay (in seconds) between retries
    """

    def __init__(self, exception, tries=10, delay=1, backoff=2, cap=120):
        """Constructor method."""
        self._exception = exception
        self._tries = int(Conf.get(const.CSM_GLOBAL_INDEX,
            const.MAX_RETRY_COUNT, tries))
        self._delay = delay
        self._backoff = backoff
        self._cap = int(Conf.get(const.CSM_GLOBAL_INDEX,
                const.RETRY_SLEEP_DURATION, cap))

    def __call__(self, func):
        @wraps(func)
        def wrap(*args, **kwargs):
            cap, max_tries, max_delay = self._cap, self._tries, self._delay
            while max_tries > 1:
                try:
                    return func(*args, **kwargs)
                except self._exception:
                    time.sleep(min(cap, max_delay))
                    max_tries -= 1
                    max_delay *= self._backoff
            return func (*args, **kwargs)
        return wrap
