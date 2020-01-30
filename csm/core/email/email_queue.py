"""
 ****************************************************************************
 Filename:          email.py
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
from csm.common.log import Log
from csm.common.email import SmtpServerConfiguration, EmailSender, EmailError
from email.mime.multipart import MIMEMultipart


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
    async def enqueue_email(self, message: MIMEMultipart, config: SmtpServerConfiguration):
        """
        Enqueue an email message to be sent
        """
        self.queue.put_nowait((message, config))

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
            self.worker = Non

    @Log.trace_method(Log.DEBUG)
    def start_worker_sync(self):
        if self.worker:
            return

        self.worker = asyncio.ensure_future(self._worker())

    async def _worker(self):
        while True:
            message, config = await self.queue.get()
            email_client = EmailSender(config)
            # TODO: cache email clients for same configs
            try:
                await email_client.send_message(message)
            except EmailError as e:
                Log.info(f'Email sending error: {e}, target: {message["To"]}')

            self.queue.task_done()
