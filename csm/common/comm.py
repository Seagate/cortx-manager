#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          comm.py
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
import sys, os
import paramiko, socket
import ftplib
import getpass
import time
import shutil
import errno
from paramiko.ssh_exception import SSHException
from csm.common.payload import *
from eos.utils.log import Log
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.common.errors import CsmError
import pika
import json
from pika.exceptions import AMQPConnectionError, AMQPError, ChannelClosedByBroker, \
    ChannelWrongStateError
from abc import ABC, ABCMeta, abstractmethod
from functools import partial
import random

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

class AmqpChannel(Channel):
    """
    Represents Amqp channel to a node for communication
    Communication to node is taken care by this class using pika    
    """

    def __init__(self, **kwargs):
        Channel.__init__(self)
        self._connection = None
        self._channel = None
        self.exchange = None
        self.exchange_queue = None
        self.routing_key = None
        self.connection_exceptions = (AMQPConnectionError, \
            ChannelClosedByBroker, ChannelWrongStateError, AttributeError)
        self.connection_error_msg = (\
            'RabbitMQ channel closed with error {}. Retrying with another host...')
        self.is_actuator = kwargs.get(const.IS_ACTUATOR, False)
        self.is_node1 = kwargs.get(const.IS_NODE1, False)
        self.node1 = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.NODE1}")
        self.node2 = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.NODE2}")
        self.hosts = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.RMQ_HOSTS}")
        self.port = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.PORT}")
        self.virtual_host = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.VHOST}")
        self.username = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.UNAME}")
        self.password = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.PASS}")
        self.exchange_type = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.EXCH_TYPE}")
        self.retry_counter = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.RETRY_COUNT}")
        self.durable = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.DURABLE}")
        self.exclusive = Conf.get(const.CSM_GLOBAL_INDEX, \
                f"{const.CHANNEL}.{const.EXCLUSIVE}")
        self._setExchangeandQueue()

    def _setExchangeandQueue(self):
        if not self.is_actuator:
            self.exchange = Conf.get(const.CSM_GLOBAL_INDEX, \
                    f"{const.CHANNEL}.{const.EXCH}")
            self.exchange_queue = Conf.get(const.CSM_GLOBAL_INDEX, \
                    f"{const.CHANNEL}.{const.EXCH_QUEUE}")
            self.routing_key = Conf.get(const.CSM_GLOBAL_INDEX, \
                    f"{const.CHANNEL}.{const.ROUTING_KEY}")
        elif self.is_actuator:
            self.exchange = Conf.get(const.CSM_GLOBAL_INDEX, \
                    f"{const.CHANNEL}.{const.ACT_REQ_EXCH}")
            self.exchange_queue = Conf.get(const.CSM_GLOBAL_INDEX, \
                    f"{const.CHANNEL}.{const.ACT_REQ_EXCH_QUEUE}") 
            if self.is_node1:
                self.routing_key = Conf.get(const.CSM_GLOBAL_INDEX, \
                        f"{const.CHANNEL}.{const.ACT_REQ_ROUTING_KEY}") + "_" + self.node1
            else:
                self.routing_key = Conf.get(const.CSM_GLOBAL_INDEX, \
                        f"{const.CHANNEL}.{const.ACT_REQ_ROUTING_KEY}") + "_" + self.node2

    def init(self):
        """
        Initialize the object from a configuration file.
        Establish connection with Rabbit-MQ server.
        """
        self._connection = None
        self._channel = None
        retry_count = 0
        while not(self._connection and self._channel) and \
            int(self.retry_counter) > retry_count:
            self.connect()
            if not (self._connection and self._channel):
                Log.warn(f"RMQ Connection Failed. Retry Attempt: {retry_count+1}" \
                    f" in {2**retry_count} seconds")
                time.sleep(2**retry_count)
                retry_count += 1
            else:
                Log.debug(f"RMQ connection is Initialized. Attempts:{retry_count+1}")
        self._declare_exchange_and_queue()

    def _declare_exchange_and_queue(self):
        if(self._connection and self._channel):
            try:
                self._channel.exchange_declare(exchange=self.exchange,
                                           exchange_type=self.exchange_type, \
                                                   durable=self.durable)
            except AMQPError as err:
                Log.error('Exchange: [{%s}], type: [ {%s} ] cannot be declared.\
                           Details: {%s}'%(self.exchange,
                                              self.exchange_type,
                                              str(err)))
            try:
                self._channel.queue_declare(queue=self.exchange_queue,
                                            exclusive=self.exclusive, \
                                                    durable=self.durable)
                self._channel.queue_bind(exchange=self.exchange,
                                         queue=self.exchange_queue,
                                         routing_key=self.routing_key)
                Log.info(f'Initialized Exchange: {self.exchange}, '
                        f'Queue: {self.exchange_queue}, routing_key: {self.routing_key}')
            except AMQPError as err:
                Log.error(f'CSM Fails to initialize the queue.\
                      Details: {err}')
                Log.exception(err)
                raise CsmError(-1, f'{err}')

    def connect(self):
        """
        Initiate the connection with RMQ and open the necessary communication channel.
        """
        try:
            ampq_hosts = [f'amqp://{self.username}:{self.password}@{host}/{self.virtual_host}'\
                for host in self.hosts]
            ampq_hosts = [pika.URLParameters(host) for host in ampq_hosts]
            random.shuffle(ampq_hosts)
            self._connection = pika.BlockingConnection(ampq_hosts)
            self._channel = self._connection.channel()
        except self.connection_exceptions as e:
            Log.error(self.connection_error_msg.format(repr(e)))

    def disconnect(self):
        """
        Disconnect the connection
        """
        try:
            if self._connection:
                consumer_tag = const.CONSUMER_TAG
                self._channel.basic_cancel(consumer_tag=consumer_tag)
                self._channel.stop_consuming()
                self._channel.close()
                self._connection.close()
                self._channel = None
                self._connection = None
                Log.debug(f"RabbitMQ connection closed.")
        except Exception as e:
            Log.error(f"Error closing RabbitMQ connection. {e}")

    def recv(self, message=None):
        raise Exception('recv not implemented for AMQP Channel')

    def connection(self):
        return self._connection

    def channel(self):
        return self._channel

    def send(self, message):
        """
        Publish the message to SSPL Rabbit-MQ queue.
        @param message: message to be published to queue.
        @type message: str
        """
        try:
            if self._channel:
                self._channel.basic_publish(exchange=self.exchange,\
                    routing_key=self.routing_key, body=json.dumps(message))
                Log.info(f"Message Publish to Xchange: {self.exchange},"\
                    f"Key: {self.routing_key}, Msg Details: {message}")
        except self.connection_exceptions as e:
            Log.error(self.connection_error_msg.format(repr(e)))
            self.init()
            self.send(message)

    def recv_file(self, remote_file, local_file):
        raise Exception('recv_file not implemented for AMQP Channel')

    def send_file(self, local_file, remote_file):
        raise Exception('send_file not implemented for AMQP Channel')

    def acknowledge(self, delivery_tag=None):
        try:
            self._channel.basic_ack(delivery_tag=delivery_tag)
        except self.connection_exceptions as e:
            Log.error(self.connection_error_msg.format(repr(e)))
            self.init()
            self.acknowledge(delivery_tag)

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

class AmqpComm(Comm):
    def __init__(self):
        Comm.__init__(self)
        self._inChannel = AmqpChannel()
        self._outChannel = AmqpChannel()
        self.plugin_callback = None
        self.delivery_tag = None
        self._is_disconnect = False

    def init(self):
        self._inChannel.init()
        self._outChannel.init()

    def send(self, message, **kwargs):
        self._outChannel.send(message)

    def _alert_callback(self, ct, ch, method, properties, body):
        """
        1. This is the callback method on which we will receive the 
           alerts from RMQ channel.
        2. This method will call AlertPlugin class function and will 
           send the alert JSON string as parameter.
        Parameters -
        1. ch - RMQ Channel
        2. method - Contains the server-assigned delivery tag
        3. properties - Contains basic properties like delivery_mode etc. 
        4. body - Actual alert JSON string
        """
        self.delivery_tag = method.delivery_tag
        self.plugin_callback(body)

    def acknowledge(self):
        self._inChannel.acknowledge(self.delivery_tag)

    def stop(self):
        self.disconnect()

    def recv(self, callback_fn=None, message=None):
        """
        Start consuming the queue messages.
        """
        try:
            consumer_tag = const.CONSUMER_TAG
            self.plugin_callback = callback_fn
            if self._inChannel.channel():
                self._inChannel.channel().basic_consume(self._inChannel.exchange_queue,\
                        partial(self._alert_callback, consumer_tag), consumer_tag=consumer_tag)
                self._inChannel.channel().start_consuming()
        except self._inChannel.connection_exceptions as e:
            """
            Currently there are 2 scenarios in which recv method will fail -
            1. When RMQ on the current node fails
            2. When we stop csm_agent
            For the 1st case csm should retry to connect to second node.
            But for the 2nd case since we are closing the app we should not
            try to re-connect.
            """
            if not self._is_disconnect:
                Log.error(self._inChannel.connection_error_msg.format(repr(e)))
                self.init()
                self.recv(callback_fn)

    def disconnect(self):
        try:
            Log.debug(f"Disconnecting AMQPSensor RMQ communication")
            self._is_disconnect = True
            self._outChannel.disconnect()
            self._inChannel.disconnect()
        except Exception as e:
            Log.exception(e)

    def connect(self):
        raise Exception('connect not implemented for AMQP Comm')

class AmqpActuatorComm(Comm):
    def __init__(self):
        Comm.__init__(self)
        self._outChannel_node1 = AmqpChannel(is_actuator = True, \
                is_node1 = True)
        self._outChannel_node2 = AmqpChannel(is_actuator = True, \
                is_node1 = False)

    def init(self):
        self._outChannel_node1.init()
        self._outChannel_node2.init()

    def send(self, message, **kwargs):
        """
        For sending storage encl we will only send it to 1 node.
        For node server request we will send it to both node 1 & 2.
        """
        if kwargs.get("is_storage_request", True):
            self._outChannel_node1.send(message)
        else:
            self._outChannel_node1.send(message)
            self._outChannel_node2.send(message)

    def acknowledge(self):
        raise Exception('acknowledge not implemented for AMQPActuator Comm')

    def stop(self):
        self.disconnect()

    def recv(self, callback_fn=None, message=None):
        raise Exception('recv not implemented for AMQPActuator Comm')

    def disconnect(self):
        try:
            Log.debug(f"Disconnecting AMQPActuator RMQ communication")
            self._outChannel_node1.disconnect()
            self._outChannel_node2.disconnect()
        except Exception as e:
            Log.exception(e)

    def connect(self):
        raise Exception('connect not implemented for AMQPActuator Comm')
