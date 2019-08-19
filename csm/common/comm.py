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
import getpass
import errno
from paramiko.ssh_exception import SSHException
from csm.common.payload import *
from csm.common.log import Log
from csm.common.conf import Conf
from csm.core.blogic import const
from csm.common.errors import CsmError
import pika
import json
from pika.exceptions import AMQPConnectionError, AMQPError
from abc import ABC, ABCMeta, abstractmethod 
from functools import partial

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
        super(SSHChannel, self).__init__(self)
        self._user = user or getpass.getuser()
        self.ftp_enabled = False
        self.allow_agent = True
        self._ssh = None
        self._node = node
        self._ssh_timeout = Conf.get(const.SSH_TIMEOUT, const.DEFAULT_SSH_TIMEOUT)
        for key, value in args.items():
            setattr(self, key, value)

    def init(self):
        raise Exception('init not implemented for SSH Channel')

    def connect(self):
        Log.debug('node=%s user=%s' %(self._node, self._user))
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect(self._node, username=self._user,\
                    timeout=self._ssh_timeout, allow_agent=self.allow_agent)
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

    def __init__(self):
        Channel.__init__(self)
        Log.init(self.__class__.__name__, '/tmp', Log.DEBUG)
        self.host = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.host") 
        self.virtual_host = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.virtual_host")
        self.username = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.username")
        self.password = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.password")
        self.exchange_type = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.exchange_type")
        self.exchange = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.exchange")
        self.exchange_queue = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.exchange_queue")
        self.routing_key = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.routing_key")
        self._connection = None 
        self._channel = None
        self.retry_counter = Conf.get(const.CSM_GLOBAL_INDEX, "CHANNEL.retry_count")

    def init(self):
        """
        Initialize the object from a configuration file.
        Establish connection with Rabbit-MQ server.
        """
        while not(self._connection and self._channel) and int(self.retry_counter) < 6:
            self.connect()
            if not (self._connection and self._channel):
                Log.warn('RMQ Connection Failed. Retry Attempt: {%d} in {%d} secs'\
                %(retry_counter, retry_counter * 2 + 60))
                time.sleep(retry_counter * 2 + 60)
                self.retry_counter += 1
        if not(self._connection and self._channel):
            Log.warn('RMQ connection Failed. SSPL communication channel\
                        could not be established.')
            Log.error('sspl-csm channel creation FAILED.\
                                  Retry attempts: 3')
            raise CsmError(-1,'RMQ connection Failed to Initialize.')
        else:
            Log.debug('RMQ connection is Initialized.')
        self._declare_exchange_and_queue()

    def _declare_exchange_and_queue(self):
        if(self._connection and self._channel):  
            try:
                self._channel.exchange_declare(exchange=self.exchange,
                                           exchange_type=self.exchange_type)
            except AMQPError as err:
                Log.error('Exchange: [{%s}], type: [ {%s} ] cannot be declared.\
                           Details: {%s}'%(self.exchange,
                                              self.exchange_type,
                                              str(err)))
            try:
                self._channel.queue_declare(queue=self.exchange_queue,
                                            exclusive=False)
                self._channel.queue_bind(exchange=self.exchange,
                                         queue=self.exchange_queue,
                                         routing_key=self.routing_key)
            except AMQPError as err:
                Log.error('CSM Fails to initialize the queue.\
                      Details: %s'.str(err))
                Log.exception(err)
                raise CsmError(-1, '%s' %err)
           
            Log.info('Initialized Exchange: {%s}, Queue: {%s},\
                     routing_key: {%s}'%(self.exchange,self.exchange_queue,
                                          self.routing_key))

    def connect(self):
        """
        Initiate the connection with RMQ and open the necessary communication channel.
        """
        try:
            self._connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,
                               virtual_host=self.virtual_host,
                               credentials=pika.PlainCredentials(self.username,self.password)))
                                                                               
            self._channel = self._connection.channel()
        except AMQPError as err:
                Log.error('RMQ connections has not established. Details  :%s ' %str(err))
                raise CsmError(-1, '%s' %err)

        Log.debug('RMQ connections has established.')
 
    def disconnect(self):
        """
        Disconnect the connection 
        """
        self._connection.close()
        self._channel.close()

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
            self._channel.basic_publish(exchange=self.exchange,routing_key=self.routing_key,
                                        body=json.dumps(message))
        except AMQPError as err:
            Log.warn('Message Publish Failed to Xchange:%s Key: %s, Msg:\
                Details: %s Error: %s' %(self.exchange,self.routing_key,message,str(err)))
        else:
              Log.info('Message Publish to Xchange:%s Key: %s, Msg:\
                Details: %s ' %(self.exchange,self.routing_key,message ))

    def recv_file(self, remote_file, local_file):
        raise Exception('recv_file not implemented for AMQP Channel')
    
    def send_file(self, local_file, remote_file):
        raise Exception('send_file not implemented for AMQP Channel')

    def acknowledge(self, delivery_tag=None):
        self._channel.basic_ack(delivery_tag=delivery_tag)

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
    def send(self, message):
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

    def init(self):
        self._inChannel.init()
        self._outChannel.init()

    def send(self, message):
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
        consumer_tag = const.CONSUMER_TAG
        self._inChannel.channel().basic_cancel(consumer_tag=consumer_tag)
        self.disconnect()
                
    def recv(self, callback_fn=None, message=None):
        """
        Start consuming the queue messages.
        """
        try:
            consumer_tag = const.CONSUMER_TAG
            self.plugin_callback = callback_fn
            self._inChannel.channel().basic_consume(self._inChannel.exchange_queue,\
                    partial(self._alert_callback, consumer_tag), consumer_tag=consumer_tag)    
            self._inChannel.channel().start_consuming()
        except AMQPConnectionError as err:
            Log.warn('Connection to RMQ has Broken. Details: {%s} ' %str(err))
            Log.exception(str(err))
            self.disconnect()

    def disconnect(self):
        try:
            self._outChannel.disconnect()
            self._inChannel.disconnect()
        except Exception as e:
            Log.exception(e)

    def connect(self):
        raise Exception('connect not implemented for AMQP Comm')
