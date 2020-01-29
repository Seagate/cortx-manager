"""
 ****************************************************************************
 Filename:          test_email_sender.py
 Description:       Unit tests related to email sender-related code.

 Creation Date:     12/16/2019
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
import asyncore
import os
import sys
import threading
import unittest
from smtpd import SMTPServer
from email import message_from_bytes
from queue import Queue, Empty

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.log import Log
from csm.common.email import SmtpServerConfiguration, EmailSender, OutOfAttemptsEmailError
from csm.core.email.email_queue import EmailSenderQueue

class TestSMTPServer(SMTPServer):
    """ Helper class - STMP server that puts messages into a queue """
    def __init__(self, *args, queue=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue

    def get_port(self):
        return self.socket.getsockname()[1]

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        message = message_from_bytes(data)
        self.queue.put(message)


class TestSMTPThread(threading.Thread):
    """ Heper class - SMTP server that runs in a separate thread """
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.server = TestSMTPServer(('localhost', 0), ('localhost', 25), queue=queue)

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
    await s.send("some_account@gmail.com", 
        "target@email.com", "Subject", "<html><body>Hi!</body></html>", "Plain text")

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
        await sender.send(TEST_SENDER, TEST_RECIPIENT,
            TEST_SUBJECT, TEST_HTML_BODY, TEST_PLAIN_BODY)
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
        t.assertTrue(False, 'Unexpected exception')
    finally:
        server_thread.abort()
        server_thread.join()

async def test_local_email_queue():
    """
    Check if EmailSenderQueue alows to queue and process 2 email messages
    """
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
        message = EmailSender.make_multipart(TEST_SENDER, TEST_RECIPIENT,
            TEST_SUBJECT, TEST_HTML_BODY, TEST_PLAIN_BODY)
        await queue_plugin.enqueue_email(message, config)
        await queue_plugin.enqueue_email(message, config)
        await queue_plugin.join_worker()

        msg = queue.get(True, 0.5)  # half second timeout
        msg = queue.get(True, 0.5)  # half second timeout
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
    try:
        sender = EmailSender(config)
        await sender.send(TEST_SENDER, TEST_RECIPIENT,
            TEST_SUBJECT, TEST_HTML_BODY, TEST_PLAIN_BODY)
    except OutOfAttemptsEmailError:
        t.assertTrue(True, 'OutOfAttemptsEmailError exception')
    except:
        t.assertTrue(False, 'Unexpected exception')

def init(args):
    pass

def run_tests(args = {}):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_local_multipart_email())
    loop.run_until_complete(test_local_email_queue())
    loop.run_until_complete(test_local_email_wo_server())

test_list = [run_tests]

if __name__ == '__main__':
    Log.init('test', '.')
    run_tests()

