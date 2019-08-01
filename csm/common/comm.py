#!/usr/bin/python

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
import sys,os
import paramiko, socket
import getpass
import errno
from paramiko.ssh_exception import SSHException
##Local ##
import csm.common.const 
from csm.common.log import Log
from csm.common.conf import Conf
from csm.common.errors import CsmError 
# Third party
import pika
import json
# Local
from pika.exceptions import AMQPConnectionError, AMQPError
from abc import ABC ,ABCMeta, abstractmethod 

class Channel(metaclass=ABCMeta):
    """ Abstract class to represent a comm channel to a node """

    @abstractmethod
    def initialize(self, config_file_path):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass             

    @abstractmethod
    def send(self, message):
        pass 

    @abstractmethod
    def send_file(self, local_file, remote_file):
        pass 

    @abstractmethod
    def recv(self, callback_fn):
        pass

    @abstractmethod
    def recv_file(self, remote_file, local_file):
        pass        
  
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

    def initialize(self, config_file_path):
        pass

    def connect(self):
        Log.debug('node=%s user=%s' %(self._node, self._user))
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self._ssh.connect(self._node, username=self._user, timeout=self._ssh_timeout, allow_agent=self.allow_agent)
            if not self.ftp_enabled: return 0
            self._sftp = self._ssh.open_sftp()

        except socket.error as e:
            rc = errno.EHOSTUNREACH if e.errno is None else e.errno
            Log.exception(e)
            raise CsmError(rc, 'can not connect to host %s' %self._node)

        except (SSHException, Exception) as e:
            Log.exception(e)
            raise CsmError(-1, 'can not connect to host %s@%s. %s' %(self._user, self._node, e))

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
        pass

    def recv(self, callback_fn):
        pass    

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


class AmqpChannel(Channel):
    """
    Represents Amqp channel to a node for communication
    Communication to node is taken care by this class using pika
    
    """
    def __init__(self):
        """
          @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        Channel.__init__(self)
        Log.init(self.__class__.__name__, '/tmp', Log.DEBUG) 
        self.host = 'localhost'
        self.virtual_host = 'SSPL'
        self.username = 'sspluser'
        self.password = 'sspl4ever'
        self.exchange_type = 'topic'
        self.exchange = 'sspl_out'
        self.exchange_queue = 'sensor-queue'
        self.routing_key = 'sensor-key'
        self._connection = None
        self._channel = None
        self.retry_counter = 1
        self.configuration =None

    def initialize(self, config_file_path):
        """
            Initialize the object from a configuration file.
            establish connection with Rabbit-MQ server.
        """
        if config_file_path:
            self.configuration = json.loads(open(config_file_path).read())

        while not(self._connection and self._channel) and self.retry_counter < 6:
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

    def _declare_exchange_and_queue(self) :

        if(self._connection and self._channel )  :  
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
        Initiate the connection with RMQ and open the necessary
        communication channel.
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


    def recv(self, callback_fn):
        """
        Start consuming the queue messages.
        """
        self._declare_exchange_and_queue()
        self._channel.basic_consume(self.exchange_queue,callback_fn)    
        self._channel.queue_declare(queue= self.exchange_queue)

    def start_consuming(self):
        """
        Start consuming the queue messages.
        """
        try:
            self._channel.start_consuming()
        except AMQPConnectionError as err:
            Log.warn('Connection to RMQ has Broken. Details: {%s} ' %str(err))
            Log.exception(str(err))
            self.disconnect()

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
        pass        
    
    def send_file(self, local_file, remote_file):
        pass  


class comm(metaclass=ABCMeta):
    """ Abstract class to represent a comm channel  

    """
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass             

    @abstractmethod
    def send(self, message):
        pass

    @abstractmethod
    def recv(self, callback_fn):
        pass

  
class AmqpComm(comm):

    def __init__(self):
        comm.__init__(self)
        self._inChannel = AmqpChannel()
        self._outChannel = AmqpChannel()

    def initialize(self, config_file_path):
        self._inChannel.initialize(config_file_path)
        self._outChannel.initialize(config_file_path)

    def send(self, message):
        self._outChannel.send(message = input_msg)

    def recv(self, callback_fn):
        self._inChannel.recieve(callback_function=callback_fn )

    def disconnect(self):
        self._outChannel.disconnect()
        self._inChannel.disconnect()

    def connect(self):
        pass   

