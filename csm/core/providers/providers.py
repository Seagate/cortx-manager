#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          providers.py
 Description:       Providers for RAS Services

 Creation Date:     22/05/2018
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

import yaml
import errno
from threading import Thread
from csm.common.errors import CsmError
from csm.common.log import Log
from csm.core.blogic.support_bundle import SupportBundle
from csm.core.blogic.email_conf import EmailConfig
from csm.common.conf import Conf
from csm.core.blogic import const
import getpass

class Request(object):
    """ Represents a request to be processed by Provider """

    def __init__(self, action, args):
        self._action = action
        self._args = args

    def action(self):
        return self._action

    def args(self):
        return self._args

class Response(object):
    """ Represents a response after processing of a request """

    def __init__(self, rc=0, output=''):
        self._rc = int(rc)
        self._output = str(output)

    def output(self):
        return self._output

    def rc(self):
        return self._rc

    def __str__(self):
        return '%d: %s' %(self._rc, self._output)

class Provider(object):
    """ Base Provider class for a given RAS functionality """

    def __init__(self, name, cluster):
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

class BundleProvider(Provider):
    """ Provider implementation for Support Bundle """

    def __init__(self, cluster):
        super(BundleProvider, self).__init__(const.SUPPORT_BUNDLE, cluster)
        self._actions = ['create', 'delete', 'list']

        components_file = const.COMPONENTS_CONF
        self._components = yaml.load(open(components_file).read())
        self._support_bundle = SupportBundle(cluster, self._components)

    def _validate_request(self, request):
        action = request.action()
        if action not in self._actions:
            raise CsmError(errno.EINVAL, 'Invalid Action %s' % request.action)

        if action == 'delete' and not request.args():
            raise CsmError(errno.EINVAL, 'insufficent argument')

    def _process_request(self, request):
        """ Processes request and returns response """
        _output = ''
        try:
            action = request.action()

            if action == 'create':
                bundle_name = request.args()[0] if request.args() else None
                _output = self._support_bundle.create(bundle_name)

            elif action == 'list':
                output = self._support_bundle.list()
                _output = '\n'.join(output)

            elif action == 'delete':
                bundle_name = request.args()[0]
                _output = self._support_bundle.delete(bundle_name)

            response = Response(0, _output)

        except CsmError as e:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

        return response

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
                _output = self._email_conf.configure(request.args(), password = password)

            elif action == 'reset':
                _output = self._email_conf.unconfigure()

            elif action == 'subscribe':
                _output = self._email_conf.subscribe(request.args())

            elif action == 'unsubscribe':
                _output = self._email_conf.unsubscribe(request.args())

            elif action == 'show':
                _output = self._email_conf.show()

            response = Response(0, _output)

        except CsmError as e:
            raise

        except OSError as e:
            Log.exception(e)
            raise CsmError(e.errno, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

        return response
