#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          node_communication_handler.py
 Description:       Contains functionality to represent a single node and to
                    handle communication with nodes.

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

import paramiko, socket
import getpass
import errno
from paramiko.ssh_exception import SSHException
from csm.common.log import Log
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.common.errors import CsmError

class Channel(object):
    """ Abstract class to represent a comm channel to a node """

    def __init__(self, node):
        self._node = node

class SSHChannel(Channel):
    """
    Represents ssh channel to a node for communication
    Communication to node is taken care by this class using paramiko
    """
    def __init__(self, node, user=None, ftp_enabled=False):
        super(SSHChannel, self).__init__(node)
        self._user = user or getpass.getuser()
        self._ftp_enabled = ftp_enabled
        self._ssh = None
        self._ssh_timeout = Conf.get(const.SSH_TIMEOUT, const.DEFAULT_SSH_TIMEOUT)

    def open(self):
        Log.debug('node=%s user=%s' %(self._node, self._user))
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self._ssh.connect(self._node, username=self._user, timeout=self._ssh_timeout)
            if not self._ftp_enabled: return 0
            self._sftp = self._ssh.open_sftp()

        except socket.error as e:
            rc = errno.EHOSTUNREACH if e.errno is None else e.errno
            Log.exception(e)
            raise CsmError(rc, 'can not connect to host %s' %self._node)

        except (SSHException, Exception) as e:
            Log.exception(e)
            raise CsmError(-1, 'can not connect to host %s@%s. %s' %(self._user, self._node, e))

    def close(self):
        """ Close the SSH channel """
        try:
            self._ssh.close()
            if self._ftp_enabled: self._sftp.close()

        except Exception as e:
            Log.exception(e)

    def execute(self, command):
        """ Execute the command at node """
        try:
            _in, _out, _err = self._ssh.exec_command(command)
            _in.close()
            rc = _out.channel.recv_exit_status()
            output = u''.join(_out.readlines()).encode('utf-8')
            error = u''.join(_err.readlines())
            _out.close()
            _err.close()
            if rc != 0: output = error
            Log.debug('$ %s\n%s' %(command, output))

        except IOError as e:
            Log.exception(e)
            raise CsmError(errno.EIO, '%s' %e)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

        return rc, output

    def get_file(self, remote_file, local_file):
        """ Get a file from node """

        if not self._ftp_enabled:
            raise CsmError(errno.EINVAL, 'Internal Error: FTP is not enabled')

        try:
            self._sftp.get(remote_file, local_file)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

    def put_file(self, local_file, remote_file):
        """ Put a file in node """

        if not self._ftp_enabled:
            raise CsmError(errno.EINVAL, 'Internal Error: FTP is not enabled')

        try:
            self._sftp.put(local_file, remote_file)

        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

