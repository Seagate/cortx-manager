#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          system.py
 Description:       Represents RAS Command and arguments to help parsing
                    command line

 Creation Date:     22/5/20202
 Author:            Prathamesh Rodi

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys
from csm.core.blogic import const
from csm.common.process import AsyncioSubprocess
from eos.utils.log import Log
from csm.common.payload import JsonMessage
from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.core.providers.providers import Response

class System:

    @staticmethod
    async def unmaintenance(command):
        """
        Wrapper method for HCTL commands.
        :param command: Command object from argparser.
        :return:
        """
        _user = const.NON_ROOT_USER
        _password = const.NON_ROOT_USER_PASS
        _command = "unmaintenance"

        Log.debug(f"executing command :-  "
                  f"{const.HCTL_NODE.format(command=_command, user=_user, pwd='*****')}")

        _unstandby_cmd = const.HCTL_NODE.format(command=_command, user=_user, pwd=_password)
        subprocess_obj = AsyncioSubprocess(_unstandby_cmd)
        _output, _err = await subprocess_obj.run()
        if _err:
            Log.error(f"_output={_output}\n _err={_err}")
            sys.stderr.write(const.HCTL_ERR_MSG)
            return
        return Response(output = "Starting System ...", rc=CSM_OPERATION_SUCESSFUL)

    @staticmethod
    async def shutdown(command):
        """
        Shutdown Node given in Command.
        #TODO:  Remove this Method in Beta and Support Shutdown through API.
        :param command: Command object from argparser.
        :return:
        """
        _user = const.NON_ROOT_USER
        _password = const.NON_ROOT_USER_PASS
        _resource_name = command.options.get("resource_name", "")
        _command = f"shutdown {_resource_name}"

        Log.debug("Validating Node ID")
        _live_node_cmd = const.HCTL_NODE.format(command='status', user=_user, pwd=_password)
        subprocess_obj = AsyncioSubprocess(_live_node_cmd)
        _output, _err = await subprocess_obj.run()
        if _err:
            Log.error( Log.error(f"_output={_output}\n _err={_err}"))
            sys.stderr.write(const.HCTL_NOT_INSTALLED)
            return
        data  = JsonMessage(_output.strip()).load()
        shutdown_flag = False
        for each_resource in data:
            if each_resource.get(const.NAME) == _resource_name:
                if not each_resource.get(const.ONLINE):
                    sys.stderr.write(const.RESOURCE_ALREADY_SHUTDOWN)
                    shutdown_flag = True
                else:
                    break
        else:
            sys.stderr.write(const.INVALID_RESOURCE)
        if shutdown_flag:
            return None

        Log.debug(f"executing command :-  "
                  f"{const.HCTL_NODE.format(command=_command, user=_user, pwd='*****')}")

        _shutdown_cmd = const.HCTL_NODE.format(command=_command, user=_user, pwd=_password)
        subprocess_obj = AsyncioSubprocess(_shutdown_cmd)
        _output, _err = await subprocess_obj.run()
        if _err:
            Log.error(f"_output={_output}\n _err={_err}")
            sys.stderr.write(const.HCTL_ERR_MSG)
            return
        return Response(output=f"Starting {_resource_name} Shutdown Process",
                        rc=CSM_OPERATION_SUCESSFUL)