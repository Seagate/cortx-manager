"""
 ****************************************************************************
 Filename:          email_queue.py
 Description:       Contains the implementation of email queue plugin.

 Creation Date:     01/17/2019
 Author:            Alexander Nogikh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import asyncio
import copy
import functools
from eos.utils.log import Log
from csm.common.email import SmtpServerConfiguration, EmailSender, EmailError
from email.message import EmailMessage


EMAIL_CLIENT_CACHE_SIZE = 10
EMAIL_BCC_BULK_LIMIT = 50

def chunk_generator(orig_list, chunk_size):
    total_size = len(orig_list)
    for i in range(0, total_size, chunk_size):
        yield orig_list[i:(i+chunk_size)]


class EmailSenderQueue:
    """
    Interface to a worker that performs mass email sending.
    For now it is just a worker coroutine, but later it might end up as an
    interface to some separate worker process.

    How to interact with this class:
    instance = EmailSenderQueue()
    await instance.start_worker()
    await instance.enqueue_email(message, smtp_config)
    # ...

    await instance.stop_worker(True)
    """
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker = None

    @Log.trace_method(level=Log.DEBUG)
    async def enqueue_email(self, message: EmailMessage, config: SmtpServerConfiguration):
        """
        Enqueue an email message to be sent
        """
        self.queue.put_nowait((message, config))

    @Log.trace_method(level=Log.DEBUG)
    async def enqueue_bulk_email(self, message: EmailMessage, recipients,
            config: SmtpServerConfiguration):
        """
        Enqueues a bulk of identical messages
        :param mesage: an instance of EmailMessage, it will not be modified
        :param recipients: a list of target recipients
        :param config:
        """
        if len(recipients) == 0:
            return

        if len(recipients) == 1:
            msg = copy.deepcopy(message)
            msg['To'] = recipients[0]
            await self.enqueue_email(msg, config)
        else:
            for bcc_list in chunk_generator(recipients, EMAIL_BCC_BULK_LIMIT):
                msg = copy.deepcopy(message)
                msg['Bcc'] = ', '.join(bcc_list)
                await self.enqueue_email(msg, config)

    @Log.trace_method(level=Log.DEBUG)
    async def start_worker(self):
        self.start_worker_sync()

    @Log.trace_method(level=Log.DEBUG)
    async def join_worker(self):
        """
        Pauses until the worker's queue becomes empty
        """
        if self.worker:
            await self.queue.join()

    @Log.trace_method(level=Log.DEBUG)
    async def stop_worker(self, graceful=False):
        if self.worker:
            if graceful:
                await self.queue.join()

            self.worker.cancel()
            self.worker = None

    @Log.trace_method(Log.DEBUG)
    def start_worker_sync(self):
        if self.worker:
            return

        self.worker = asyncio.ensure_future(self._worker())

    async def _worker(self):
        config = None

        @functools.lru_cache(EMAIL_CLIENT_CACHE_SIZE)
        def _get_client(config):
            return EmailSender(config)

        while True:
            message, config = await self.queue.get()
            email_client = _get_client(config)

            try:
                await email_client.send_message(message)
            except EmailError as e:
                Log.info(f'Email sending error: {e}, target: {message["To"]}')

            self.queue.task_done()
