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

import asyncio
import asyncore
import threading
import unittest
from email import message_from_bytes
from queue import Empty, Queue
from smtpd import SMTPServer

from csm.common.email import EmailSender, OutOfAttemptsEmailError, SmtpServerConfiguration
from csm.core.email.email_queue import EmailSenderQueue


class TestSMTPServer(SMTPServer):
    """Helper class - SMTP server that puts messages into a queue"""
    def __init__(self, *args, queue=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue

    def get_port(self):
        return self.socket.getsockname()[1]

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        message = message_from_bytes(data)
        self.queue.put(message)


class TestSMTPThread(threading.Thread):
    """Helper class - SMTP server that runs in a separate thread"""
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.server = TestSMTPServer(('localhost', 0), ('localhost', 25), queue=queue)
        self._should_stop = None

    def get_port(self):
        return self.server.get_port()

    def run(self):
        self._should_stop = False
        while not self._should_stop:
            asyncore.loop(timeout=0.1, count=1)

    def abort(self):
        self._should_stop = True


async def remote_email_send_example():
    # TODO: these credentials are not real
    config = SmtpServerConfiguration()
    config.smtp_host = "smtp.gmail.com"
    config.smtp_port = 465
    config.smtp_login = "some_account@gmail.com"
    config.smtp_password = "SomePassword"
    config.smtp_use_ssl = True

    s = EmailSender(config)
    await s.send("some_account@gmail.com", "target@email.com", "Subject",
                 "<html><body>Hi!</body></html>", "Plain text")


async def local_email_send_example():
    # Run python3 -m smtpd -c DebuggingServer -n localhost:9999
    config = SmtpServerConfiguration()
    config.smtp_host = "localhost"
    config.smtp_port = 9999
    config.smtp_login = None
    config.smtp_use_ssl = False

    s = EmailSender(config)
    await s.send("some_account@gmail.com",
                 "target@email.com", "Subject", "<html><body>Hi!</body></html>", "Plain text")

t = unittest.TestCase()

TEST_SUBJECT = "Email subject"
TEST_HTML_BODY = "<html><body>Hello!</body></html>"
TEST_PLAIN_BODY = "Some plain body"
TEST_SENDER = "sender@mail.com"
TEST_RECIPIENT = "to@mail.com"


async def test_local_multipart_email():
    queue = Queue()
    server_thread = TestSMTPThread(queue)
    server_thread.start()

    config = SmtpServerConfiguration()
    config.smtp_host = "localhost"
    config.smtp_login = None
    config.smtp_use_ssl = False
    try:
        config.smtp_port = server_thread.get_port()
        sender = EmailSender(config)
        await sender.send(TEST_SENDER, TEST_RECIPIENT, TEST_SUBJECT, TEST_HTML_BODY,
                          TEST_PLAIN_BODY)
        msg = queue.get(True, 1)  # 1 second timeout

        contents = {}
        for part in msg.walk():
            contents[part.get_content_type()] = part.get_payload()

        t.assertIn('text/plain', contents)
        t.assertEqual(contents['text/plain'], TEST_PLAIN_BODY)
        t.assertIn('text/html', contents)
        t.assertEqual(contents['text/html'], TEST_HTML_BODY)
        t.assertEqual(msg['Subject'], TEST_SUBJECT)
        t.assertEqual(msg['To'], TEST_RECIPIENT)
        t.assertEqual(msg['From'], TEST_SENDER)
    except:
        t.fail('Unexpected exception')
    finally:
        server_thread.abort()
        server_thread.join()


async def test_local_email_queue():
    """Check if EmailSenderQueue allows to queue and process 2 email messages"""
    queue_plugin = EmailSenderQueue()
    await queue_plugin.start_worker()

    queue = Queue()
    server_thread = TestSMTPThread(queue)
    server_thread.start()

    config = SmtpServerConfiguration()
    config.smtp_host = "localhost"
    config.smtp_login = None
    config.smtp_use_ssl = False
    try:
        config.smtp_port = server_thread.get_port()
        message = EmailSender.make_multipart(TEST_SENDER, TEST_RECIPIENT, TEST_SUBJECT,
                                             TEST_HTML_BODY, TEST_PLAIN_BODY)
        await queue_plugin.enqueue_email(message, config)
        await queue_plugin.enqueue_email(message, config)
        await queue_plugin.join_worker()

        queue.get(True, 0.5)  # half second timeout
        queue.get(True, 0.5)  # half second timeout
    except Empty:
        t.fail('Email messages were not delivered')
    finally:
        await queue_plugin.stop_worker()
        server_thread.abort()
        server_thread.join()


async def test_local_email_wo_server():
    config = SmtpServerConfiguration()
    config.smtp_host = "localhost"
    config.smtp_port = 25255
    config.smtp_login = None
    config.smtp_use_ssl = False
    email_error = False
    try:
        sender = EmailSender(config)
        await sender.send(TEST_SENDER, TEST_RECIPIENT, TEST_SUBJECT, TEST_HTML_BODY,
                          TEST_PLAIN_BODY)
    except OutOfAttemptsEmailError:
        email_error = True
    except:
        t.fail('Unexpected exception')
    if not email_error:
        t.fail('OutOfAttemptsEmailError not raised')


def run_tests():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_local_multipart_email())
    loop.run_until_complete(test_local_email_queue())
    loop.run_until_complete(test_local_email_wo_server())


test_list = [run_tests]
