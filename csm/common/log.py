#!/usr/bin/python

"""
 ****************************************************************************
 Filename:          log.py
 _description:      Logger Implementation

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

import os, errno
import logging.handlers
import inspect

class Log:
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARN = logging.WARNING
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET

    logger = None

    @staticmethod
    def init(service_name, log_path='/var/log', level=DEBUG):
        """ Initialize logging to log to syslog """

        try:
            if not os.path.exists(log_path): os.makedirs(log_path)
        except OSError as err:
            if err.errno != errno.EEXIST: raise

        format = '%(asctime)s: %(name)s %(levelname)s %(message)s'
        formatter = logging.Formatter(format)

        log_file = os.path.join(log_path, '%s.log' %service_name)
        fileHandler = logging.FileHandler(log_file)
        fileHandler.setFormatter(formatter)

        Log.logger = logging.getLogger(service_name)
        Log.logger.setLevel(level)

        Log.logger.addHandler(fileHandler)

    @staticmethod
    def debug(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.debug('[%s] %s' %(caller, msg), *args, **kwargs)

    @staticmethod
    def info(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.info('[%s] %s' %(caller, msg), *args, **kwargs)

    @staticmethod
    def warn(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.warn('[%s] %s' %(caller, msg), *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.error('[%s] %s' %(caller, msg), *args, **kwargs)

    @staticmethod
    def critical(msg, *args, **kwargs):
        """ Logs a message with level CRITICAL on this logger. """
        caller = inspect.stack()[1][3]
        Log.logger.critical('[%s] %s' %(caller, msg), *args, **kwargs)

    @staticmethod
    def exception(e, *args, **kwargs):
        """ Logs a message with level ERROR on this logger. """
        caller = inspect.stack()[1][3]
        Log.logger.exception('[%s] [%s] %s' %(caller, e.__class__.__name__, e))

    @staticmethod
    def console(msg, *args, **kwargs):
        """ Logs a message with level ERROR on this logger. """
        caller = inspect.stack()[1][3]
        Log.logger.debug('[%s] %s' %(caller, msg), *args, **kwargs)
        print('[%s] %s' %(caller, msg))
