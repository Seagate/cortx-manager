#!/usr/bin/env python3

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
from functools import wraps
import json

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
    def init(service_name, log_path='/var/log', level="DEBUG", file_size_in_mb=10,
             backup_count=10):
        """ Initialize logging to log to syslog """
        try:
            if not os.path.exists(log_path): os.makedirs(log_path)
        except OSError as err:
            if err.errno != errno.EEXIST: raise
        max_bytes = file_size_in_mb * 1024 * 1024
        Log.logger = Log._get_logger(log_path, service_name, max_bytes,
                                         backup_count, getattr(Log, level))

    @staticmethod
    def _get_logger(log_path: str, file_name: str, max_bytes: int,
                        backup_count: int, log_level):
        """
        This Function Creates the Logger for Log Files.
        :param log_path: Log Path for Log File :type: Str
        :param file_name: File name for Log Files. :type: Str
        :param max_bytes: Max Size for each rotating File. :type: int
        :param backup_count: Number of Files to be kept for backup :type: int
        :param log_level: Log Class Instance :type: Class(Log)
        :return: Logger Object
        """
        log_format = '%(asctime)s: %(name)s %(levelname)s %(message)s'
        formatter = logging.Formatter(log_format)
        log_file = os.path.join(log_path, f"{file_name}.log")
        file_handler = logging.handlers.RotatingFileHandler(log_file,
                                                            maxBytes=max_bytes,
                                                            backupCount=backup_count)
        file_handler.setFormatter(formatter)
        file_handler.doRollover()
        logger = logging.getLogger(f"{file_name}")
        logger.setLevel(log_level)
        logger.addHandler(file_handler)
        return logger

    @staticmethod
    def debug(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.debug(f'[{caller}] {msg}', *args, **kwargs)

    @staticmethod
    def info(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.info(f'[{caller}] {msg}', *args, **kwargs)

    @staticmethod
    def warn(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.warn(f'[{caller}] {msg}', *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        caller = inspect.stack()[1][3]
        Log.logger.error(f'[{caller}] {msg}', *args, **kwargs)

    @staticmethod
    def critical(msg, *args, **kwargs):
        """ Logs a message with level CRITICAL on this logger. """
        caller = inspect.stack()[1][3]
        Log.logger.critical(f'[{caller}] {msg}', *args, **kwargs)

    @staticmethod
    def exception(e, *args, **kwargs):
        """ Logs a message with level ERROR on this logger. """
        caller = inspect.stack()[1][3]
        Log.logger.exception(f'[{caller}] [{e.__class__.__name__}] e')

    @staticmethod
    def console(msg, *args, **kwargs):
        """ Logs a message with level ERROR on this logger. """
        caller = inspect.stack()[1][3]
        Log.logger.debug(f'[{caller}] {msg}', *args, **kwargs)
        print(f'[{caller}] {msg}')

    @staticmethod
    def trace_method(level, exclude_args=[], truncate_at=35):
        """
        A wrapper method that logs each invocation and exit of the wrapped function.
        :param: level - Level of logging (e.g. Logger.DEBUG)
        :param: exclude_args - Array of arguments to exclude from the logging
                (it can be useful e.g. for hiding passwords from the log file)
        :param: truncate_at - Allows to truncate the printed argument values. 35 by default.

        Example usage:
        @Logger.trace_method(Logger.DEBUG)
        def some_function(arg_1, arg_2):
            pass
        """
        def _fmt_value(obj):
            str_value = repr(obj)
            if len(str_value) < truncate_at:
                return str_value
            else:
                return str_value[:truncate_at] + "..."

        def _print_start(func, *args, **kwargs):
            pos_args = [_fmt_value(arg) for arg in args]
            # TODO: handle exclusion of positional arguments as well
            kw_args = [key + "=" + _fmt_value(kwargs[key]) for key in kwargs
                if key not in exclude_args]

            message = "[{}] Invoked with ({})".format(
                func.__qualname__, ",".join(pos_args + kw_args))
            Log.logger.log(level, message)

        def _print_end(func, response):
            message = "[{}] Returned {}".format(func.__qualname__, _fmt_value(response))
            Log.logger.log(level, message)

        # This function will be used as a decorator
        def decorator(func):
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                _print_start(func, *args, **kwargs)
                resp = func(*args, **kwargs)
                _print_end(func, resp)
                return resp

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                _print_start(func, *args, **kwargs)
                resp = await func(*args, **kwargs)
                _print_end(func, resp)
                return resp

            # If the function is async, it needs special treatment
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator
