# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

import errno
from threading import Thread
from csm.common.errors import CsmError
from cortx.utils.log import Log
from csm.core.blogic.email_conf import EmailConfig
from csm.core.blogic import const
import getpass


class Request(object):
    """ Represents a request to be processed by Provider """

    def __init__(self, action, args, options=None):
        self._action = action
        self._args = args
        self._options = options

    def action(self):
        return self._action

    def args(self):
        return self._args

    def options(self):
        return self._options


class Response(object):
    """ Represents a response after processing of a request """
    # TODO:Wherever this class is used for raising the error; that will be
    #  replaced with proper CsmError type

    def __init__(self, rc=0, output=''):
        self._rc = int(rc)
        self._output = output

    def output(self):
        return self._output

    def rc(self):
        return self._rc

    def __str__(self):
        return '%d: %s' % (self._rc, self._output)


class Provider(object):
    """ Base Provider class for a given RAS functionality """

    def __init__(self, name, cluster=None):
        self._name = name
        self._cluster = cluster

    def process_request(self, request, callback=None):
        """
        Primary interface for processing of queries/requests
        Derived class will implement _process_request which will
        perform the required processing.
        """

        self._validate_request(request)
        if callback is None:
            return self.__process_request(request)
        else:
            Thread(target=self.__process_request_bg(request, callback))

    def __process_request(self, request):
        try:
            response = self._process_request(request)
        except CsmError as e:
            response = Response(e.rc(), e.error())
        return response

    def __process_request_bg(self, request, callback):
        """ Process request in background and invoke callback once done """
        response = self.__process_request(request)
        callback(response)


class EmailProvider(Provider):
    """ Provider implementation for Email Configuration """

    def __init__(self, cluster):
        super(EmailProvider, self).__init__(const.EMAIL_CONFIGURATION, cluster)
        self._actions = ['config', 'reset', 'show', 'subscribe', 'unsubscribe']
        self._email_conf = EmailConfig()

    def _validate_request(self, request):
        action = request.action()
        if action not in self._actions:
            raise CsmError(errno.EINVAL, 'Invalid Action %s' % request.action)

        if action == 'config' and len(request.args()) < 3:
            raise CsmError(errno.EINVAL, 'insufficent argument')

        if (action == 'unsubscribe' or action == 'subscribe') and not request.args():
            raise CsmError(errno.EINVAL, 'insufficent argument')

    def _process_request(self, request):
        """ Processes request and returns response """
        _output = ''
        try:
            action = request.action()

            if action == 'config':
                password = getpass.getpass('Password: ')
                _output = self._email_conf.configure(request.args(), password=password)

            elif action == 'reset':
                _output = self._email_conf.unconfigure()

            elif action == 'subscribe':
                _output = self._email_conf.subscribe(request.args())

            elif action == 'unsubscribe':
                _output = self._email_conf.unsubscribe(request.args())

            elif action == 'show':
                _output = self._email_conf.show()

            response = Response(0, _output)

        except CsmError:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' % e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' % e)

        return response
