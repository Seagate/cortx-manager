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

import sys, os
import paramiko, socket
import ftplib
import getpass
import time
import shutil
import errno
from paramiko.ssh_exception import SSHException
from csm.common.payload import *
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from csm.core.blogic import const
from csm.common.errors import CsmError
import json
from abc import ABC, ABCMeta, abstractmethod
from functools import partial
import random
from cortx.utils.message_bus import MessageBus, MessageProducer, MessageConsumer
from cortx.utils.message_bus.error import MessageBusError

class Channel(metaclass=ABCMeta):
    """ Abstract class to represent a comm channel to a node """

    @abstractmethod
    def init(self):
        raise Exception('init not implemented in Channel class')

    @abstractmethod
    def connect(self):
        raise Exception('connect not implemented in Channel class')

    @abstractmethod
    def disconnect(self):
        raise Exception('disconnect not implemented in Channel class')

    @abstractmethod
    def send(self, message):
        raise Exception('send not implemented in Channel class')

    @abstractmethod
    def send_file(self, local_file, remote_file):
        raise Exception('send_file not implemented in Channel class')

    @abstractmethod
    def recv(self, message=None):
        raise Exception('recv not implemented in Channel class')

    @abstractmethod
    def recv_file(self, remote_file, local_file):
        raise Exception('recv_file not implemented in Channel class')

    def acknowledge(self, delivery_tag=None):
        raise Exception('acknowledge not implemented for Channel class')

class SSHChannel(Channel):
    """
    Represents ssh channel to a node for communication
    Communication to node is taken care by this class using paramiko
    """
    def __init__(self, node, user=None, **args):
        super(SSHChannel, self).__init__()
        self._user = user or getpass.getuser()
        self.ftp_enabled = False
        self.allow_agent = True
        self._ssh = None
        self._node = node
        self.look_for_keys = args.get('look_for_keys', False)
        self.key_filename = args.get('key_filename', None)
        self._ssh_timeout = Conf.get(const.CSM_GLOBAL_INDEX,
                const.SSH_TIMEOUT, const.DEFAULT_SSH_TIMEOUT)
        for key, value in args.items():
            setattr(self, key, value)

    def init(self):
        raise Exception('init not implemented for SSH Channel')

    def connect(self):
        Log.debug('node=%s user=%s' %(self._node, self._user))
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect(self._node, username=self._user,
                    timeout=self._ssh_timeout, allow_agent=self.allow_agent,
                    key_filename=self.key_filename)
            if not self.ftp_enabled: return 0
            self._sftp = self._ssh.open_sftp()
        except socket.error as e:
            rc = errno.EHOSTUNREACH if e.errno is None else e.errno
            Log.exception(e)
            raise CsmError(rc, 'can not connect to host %s' %self._node)
        except (SSHException, Exception) as e:
            Log.exception(e)
            raise CsmError(-1, 'can not connect to host %s@%s. %s'\
                    %(self._user, self._node, e))

    def disconnect(self):
        """ Close the SSH channel """
        try:
            self._ssh.close()
            if self.ftp_enabled: self._sftp.close()
        except Exception as e:
            Log.exception(e)

    def execute(self, command, **kwargs):
        """ Execute the command at node """
        try:
            _in, _out, _err = self._ssh.exec_command(command,
                                                     timeout=kwargs.get("timeout", None))
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

    def send(self, message):
        raise Exception('send not implemented for SSH Channel')

    def recv(self, message=None):
        raise Exception('recv not implemented for SSH Channel')

    def recv_file(self, remote_file, local_file):
        """ Get a file from node """
        if not self.ftp_enabled:
            raise CsmError(errno.EINVAL, 'Internal Error: FTP is not enabled')
        try:
            self._sftp.get(remote_file, local_file)
        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

    def send_file(self, local_file, remote_file):
        """ Put a file in node """
        if not self._ftp_enabled:
            raise CsmError(errno.EINVAL, 'Internal Error: FTP is not enabled')
        try:
            self._sftp.put(local_file, remote_file)
        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' %e)

    def acknowledge(self, delivery_tag=None):
        raise Exception('acknowledge not implemented for SSH Channel')

class FILEChannel(Channel):
    def __init__(self, *args, **kwargs):
        super(FILEChannel, self).__init__()

    def init(self):
        raise Exception('init not implemented in File Channel class')

    def connect(self):
        pass

    def send(self, message):
        raise Exception('send not implemented in FIle Channel class')

    def send_file(self, local_file_path, remote_directory):
        """
        Moves the FIle from Local File Path to Path Given
        :param local_file_path:
        :param remote_directory:
        :return:
        """
        shutil.move(local_file_path, remote_directory)

    def disconnect(self):
        pass

    def recv(self, message=None):
        raise Exception('recv not implemented in Channel class')

    def recv_file(self, remote_file, local_file):
        raise Exception('recv_file not implemented in Channel class')

    def acknowledge(self, delivery_tag=None):
        raise Exception('acknowledge not implemented for Channel class')

class FTPChannel(Channel):
    """
    Represents FTP channel for communication.
    Communication to FTP server is taken care by this class using ftplib.
    """

    def __init__(self, host, user, password, port=21, **kwargs):
        super(FTPChannel, self).__init__()
        self._host = host
        self._port = port
        self._user = user
        self._ftp = None
        self._password = password
        self._ispassive = kwargs.get("is_passive", False)

    def init(self):
        raise Exception('init not implemented in FTP Channel class')

    def connect(self):
        Log.debug('host=%s user=%s' % (self._host, self._user))
        try:
            self._ftp = ftplib.FTP()
            self._ftp.connect(self._host, self._port)
            self._ftp.login(self._user, self._password)
            self._ftp.set_pasv(self._ispassive)
        except ftplib.Error as e:
            Log.error(f"Cannot Connect to the host {self._host}")
            rc = errno.EHOSTUNREACH
            raise CsmError(rc, f"Cannot Connect to the host {self._host}")
        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, f"Cannot Connect to  {self._user}@{self._host}")

    def disconnect(self):
        try:
            self._ftp.close()
        except Exception as e:
            Log.exception(e)

    def send(self, message):
        raise Exception('send not implemented in FTP Channel class')

    def send_file(self, local_file_path, remote_directory):
        """Send Files to FTP server """
        if not self._ftp:
            raise CsmError(errno.EINVAL, 'Internal Error: FTP is not enabled')
        try:
            if remote_directory:
                self._ftp.cwd(remote_directory)
            remote_file = os.path.join(remote_directory,
                           local_file_path.split(os.sep)[-1])
            with open(local_file_path, 'rb') as file_obj:
                self._ftp.storbinary(f"STOR {remote_file}", file_obj)
        except Exception as e:
            Log.exception(e)
            raise CsmError(-1, '%s' % e)

    def recv(self, message=None):
        raise Exception('recv not implemented in Channel class')

    def recv_file(self, remote_file, local_file):
        raise Exception('recv_file not implemented in Channel class')

    def acknowledge(self, delivery_tag=None):
        raise Exception('acknowledge not implemented for Channel class')

class Comm(metaclass=ABCMeta):
    """ Abstract class to represent a comm channel """
    @abstractmethod
    def init(self):
        raise Exception('init not implemented in Comm class')

    @abstractmethod
    def connect(self):
        raise Exception('connect not implemented in Comm class')

    @abstractmethod
    def disconnect(self):
        raise Exception('disconnect not implemented in Comm class')

    @abstractmethod
    def send(self, message, **kwargs):
        raise Exception('send not implemented in Comm class')

    @abstractmethod
    def recv(self, callback_fn=None, message=None):
        raise Exception('recv not implemented in Comm class')

    @abstractmethod
    def acknowledge(self):
        raise Exception('acknowledge not implemented in Comm class')

class MessageBusComm(Comm):
    """
    MessageBusComm Classprovides an easy-to-use interface which can be used to
    send or receive messages across any component on a node to any other
    component on the other nodes
    """
    def __init__(self, message_server_endpoints):
        Comm.__init__(self)
        self.message_callback = None
        self.producer_id = None
        self.message_type = None
        self.consumer_id = None
        self.consumer_group = None
        self.consumer_message_types = None
        self.producer = None
        self.consumer = None
        self.recv_timeout = 0.5
        self.initialize_message_bus(message_server_endpoints)

    def init(self, **kwargs):
        """
        Initializes the producer and consumer communication.
        :param kwargs:
            type: producer|consumer|both(default)
            producer_id: String representing ID that uniquely identifies a producer
            messge_type : This is essentially equivalent to the queue/topic
            name, e.g. "sensor-key"
            method[Optional] : Signifies if message needs to be sent in "sync"
            (default) or in "async" manner.
            consumer_id : String representing ID that uniquely identifies a consumer
            consumer_group : String representing Consumer Group ID.
                Group of consumers can process messages
            message_type : This is essentially equivalent to the queue/topic
                name, e.g. "delete"
            auto_ack[Optional] : True or False. Message should be automatically
                acknowledged (default is False)
            offset[Optional] : Can be set to "earliest" (default) or "latest".
                ("earliest" will cause messages to be read from the beginning)
        """
        self.type = kwargs.get(const.TYPE)
        #Producer related configuration
        self.producer_id = kwargs.get(const.PRODUCER_ID)
        self.message_type = kwargs.get(const.MESSAGE_TYPE)
        self.method = kwargs.get(const.METHOD, const.ASYNC)
        #Consumer related configuration
        self.consumer_id = kwargs.get(const.CONSUMER_ID)
        self.consumer_group = kwargs.get(const.CONSUMER_GROUP)
        self.consumer_message_types = kwargs.get(const.CONSUMER_MSG_TYPES)
        self.auto_ack = kwargs.get(const.AUTO_ACK, False)
        self.offset = kwargs.get(const.OFFSET, const.EARLIEST)
        self.callback = kwargs.get(const.CONSUMER_CALLBACK)
        self.is_blocking = kwargs.get(const.BLOCKING, False)
        self.is_running = True
        if self.type == const.PRODUCER:
            self._initialize_producer()
        elif self.type == const.CONSUMER:
            self._initialize_consumer()

    def initialize_message_bus(self, message_server_endpoints):
        """ Initializing Messagebus server """
        Log.info(f"Initializing Messagebus server with endpoints:{message_server_endpoints}")
        MessageBus.init(message_server_endpoints)

    def _initialize_producer(self):
        """ Initializing Producer """
        self.producer = MessageProducer(producer_id=self.producer_id,\
                message_type=self.message_type, method=self.method)
        Log.info(f"Producer Initialized - Produce ID : {self.producer_id},"\
                f" Message Type: {self.message_type}, method: {self.method}")

    def _initialize_consumer(self):
        """ Initializing Consumer """
        self.consumer = MessageConsumer(consumer_id=self.consumer_id,\
                consumer_group=self.consumer_group, message_types=self.consumer_message_types,
                auto_ack=self.auto_ack, offset=self.offset)
        Log.info(f"Consumer Initialized - Consumer ID : {self.consumer_id},"\
                f" Consumer Group: {self.consumer_group}, Auto Ack: {self.auto_ack}"\
                f" Message Types: {self.consumer_message_types}, Offset: {self.offset}")
        if self.is_blocking:
            self.recv_timeout = 0

    def connect(self):
        raise Exception('connect not implemented for MessageBusComm')

    def disconnect(self):
        raise Exception('Disconnect not implemented for MessageBusComm')

    def send(self, message, **kwargs):
        """
        Sends list of messages to a specifed message type.
        :param message: List of messages.
        :param kwargs: For future use. If we need some more config.
        """
        if self.producer:
            if self.is_running:
                self.producer.send(message)
                Log.debug(f"Messages: {message} sent over {self.message_type} channel.")
            else:
                self.producer = None
        else:
            Log.error("Message Bus Producer not initialized.")

    def recv(self, callback_fn=None, message=None):
        """
        Receives messages from message bus
        :param callback_fn: This is the callback method on which we will
        receive messages from message bus.
        """
        if self.consumer:
            while True:
                try:
                    if self.is_running:
                        message = self.consumer.receive(self.recv_timeout)
                        if message:
                            decoded_message = message.decode('utf-8')
                            Log.debug(f"Received Message: {decoded_message}")
                            callback_fn(decoded_message)
                        else:
                            #For non-blocking calls.
                            time.sleep(1)
                    else:
                        #Stop called need to break
                        self.consumer = None
                        break
                except MessageBusError as ex:
                    Log.error(f"Message consuming failed. {ex}")
                    continue
        else:
            Log.error("Message Bus Consumer not initialized.")

    def acknowledge(self):
        """ Acknowledge the read messages. """
        if self.consumer:
            self.consumer.ack()

    def stop(self):
        #Stopping the sending and receiving of messages.
        self.is_running = False
