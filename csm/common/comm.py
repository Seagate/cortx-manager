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

import time
import shutil
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from csm.core.blogic import const
from abc import ABCMeta, abstractmethod
from cortx.utils.message_bus import MessageBus, MessageProducer, MessageConsumer
from cortx.utils.message_bus.error import MessageBusError


class Channel(metaclass=ABCMeta):
    """Abstract class to represent a comm channel to a node."""

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

    @abstractmethod
    def acknowledge(self, delivery_tag=None):
        raise Exception('acknowledge not implemented for Channel class')


class FILEChannel(Channel):
    def __init__(self, *args, **kwargs):
        super(FILEChannel, self).__init__()

    def init(self):
        raise Exception('init not implemented in File Channel class')

    def connect(self):
        pass

    def send(self, message):
        raise Exception('send not implemented in FIle Channel class')

    def send_file(self, local_file, remote_file):
        """
        Move the file from local file path to the path given.

        :param local_file:
        :param remote_file:
        :return:
        """
        shutil.move(local_file, remote_file)

    def disconnect(self):
        pass

    def recv(self, message=None):
        raise Exception('recv not implemented in Channel class')

    def recv_file(self, remote_file, local_file):
        raise Exception('recv_file not implemented in Channel class')

    def acknowledge(self, delivery_tag=None):
        raise Exception('acknowledge not implemented for Channel class')


class Comm(metaclass=ABCMeta):
    """Abstract class to represent a comm channel."""

    @abstractmethod
    def init(self, **kwargs):
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
    Message bus client.

    MessageBusComm Class provides an easy-to-use interface which can be used to
    send or receive messages across any component on a node to any other
    component on the other nodes.
    """

    def __init__(self, message_server_endpoints, unblock_consumer=False):
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
        self.unblock_consumer = unblock_consumer
        self.initialize_message_bus(message_server_endpoints)

    def init(self, **kwargs):
        """
        Initialize the producer and consumer communication.

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
        # Producer related configuration
        self.producer_id = kwargs.get(const.PRODUCER_ID)
        self.message_type = kwargs.get(const.MESSAGE_TYPE)
        self.method = kwargs.get(const.METHOD, const.ASYNC)
        # Consumer related configuration
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
        """Initialize Messagebus server."""
        Log.info(
            f"Initializing Messagebus server with endpoints:{message_server_endpoints} and recieve timeout = {self.recv_timeout}")
        MessageBus.init(message_server_endpoints)

    def _initialize_producer(self):
        """Initialize Producer."""
        self.producer = MessageProducer(
            producer_id=self.producer_id, message_type=self.message_type, method=self.method)
        Log.info(f"Producer Initialized - Produce ID : {self.producer_id},"
                 f" Message Type: {self.message_type}, method: {self.method}")

    def _initialize_consumer(self):
        """Initialize Consumer."""
        self.consumer = MessageConsumer(
            consumer_id=self.consumer_id, consumer_group=self.consumer_group,
            message_types=self.consumer_message_types,
            auto_ack=self.auto_ack, offset=self.offset)
        Log.info(f"Consumer Initialized - Consumer ID : {self.consumer_id},"
                 f" Consumer Group: {self.consumer_group}, Auto Ack: {self.auto_ack}"
                 f" Message Types: {self.consumer_message_types}, Offset: {self.offset}")
        if self.is_blocking:
            self.recv_timeout = 0

    def connect(self):
        raise Exception('connect not implemented for MessageBusComm')

    def disconnect(self):
        raise Exception('Disconnect not implemented for MessageBusComm')

    def send(self, message, **kwargs):
        """
        Send a list of messages to a specifed message type.

        :param message: List of messages.
        :param kwargs: For future use. If we need some more config.
        """
        if self.producer:
            if self.is_running:
                self.producer.send(message)
                Log.debug(
                    f"Messages: {message} sent over {self.message_type} channel.")
            else:
                self.producer = None
        else:
            Log.error("Message Bus Producer not initialized.")

    def recv(self, callback_fn=None, message=None):
        """
        Receive messages from message bus.

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
                            if self.unblock_consumer:
                                break
                            # For non-blocking calls.
                            time.sleep(1)
                    else:
                        # Stop called need to break
                        self.consumer = None
                        break
                except MessageBusError as ex:
                    Log.error(f"Message consuming failed. {ex}")
                    continue
        else:
            Log.error("Message Bus Consumer not initialized.")

    def acknowledge(self):
        """Acknowledge the read messages."""
        if self.consumer:
            self.consumer.ack()

    def stop(self):
        # Stopping the sending and receiving of messages.
        self.is_running = False
