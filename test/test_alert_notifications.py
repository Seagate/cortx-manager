"""
 ****************************************************************************
 Filename:          test_alert_notifications.py
 Description:       Unit tests related to alert notifications.

 Creation Date:     01/22/2019
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
import os
import sys
import threading
import unittest


sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from eos.utils.log import Log
from csm.common.observer import Observable
from csm.common.template import Template
from csm.common.email import SmtpServerConfiguration, EmailSender, OutOfAttemptsEmailError
from csm.core.blogic.models.alerts import IAlertStorage, Alert
from csm.core.data.models.system_config import SystemConfigSettings, Notification, EmailConfig
from csm.core.services.alerts import AlertMonitorService, AlertEmailNotifier


class MockAlertRepository(IAlertStorage):
    async def store(self, alert):
        pass

    async def retrieve(self, alert_id):
        return None

    async def retrieve_by_hw(self, hw_id):
        return None

    async def update(self, alert):
        await self.db(AlertModel).store(alert)

    async def update_by_hw_id(self, hw_id, update_params):
        pass

    async def retrieve_by_range(self, *args, **kwargs):
        return []

    async def count_by_range(self, *args, **kwargs):
        return 0

    async def retrieve_all(self) -> list:
        return []

class MockAlertPlugin:
    def __init__(self, alert):
        self.monitor_callback = None
        self.alert = alert

    def init(self, callback_fn):
        self.monitor_callback = callback_fn

    def process_request(self, cmd):
        if cmd == 'listen':
            self.monitor_callback(self.alert)

class MockEmailQueue(Observable):
    async def enqueue_email(self, message, config):
        self._notify_listeners(message, config, loop=asyncio.get_event_loop())

class MockSystemConfigManager:
    def __init__(self, value):
        self.value = value

    async def get_current_config(self):
        return self.value

t = unittest.TestCase()

RAW_ALERT = {
    "alert_uuid": "abcd",
    "sensor_info": "hw01234",
    "state": "missing",
    "created_time": 0,
    "updated_time": 0,
    "resolved": False,
    "acknowledged": False,
    "severity": "no"
}

ALERT_MODEL = None

email_config = EmailConfig()
email_config.stmp_server = "localhost"
email_config.smtp_port = 1234
email_config.smtp_protocol = "tls"
email_config.smtp_sender_email = "from@email.com"
email_config.smtp_sender_password = "1234"
email_config.email = "to@email.com"
email_config.weekly_email = False

def init(args):
    pass

async def test_alert_monitor_service():
    """ Tests if AlertMonitorService notifies its observers about new alerts """
    mock_repo = MockAlertRepository()
    mock_plugin = MockAlertPlugin(RAW_ALERT)

    been_called = False
    def handle_alert_cb(alert):
        nonlocal been_called
        global ALERT_MODEL
        t.assertIsNotNone(alert)

        been_called = True
        ALERT_MODEL = alert

    monitor_service = AlertMonitorService(mock_repo, mock_plugin)
    monitor_service.add_listener(handle_alert_cb)
    monitor_service.start()
    await asyncio.sleep(1)  # We need to release event loop for some time

    monitor_service.stop()
    t.assertTrue(been_called, "AlertMonitorService did not notify its observers")


async def test_email_notification():
    t.assertIsNotNone(ALERT_MODEL, 'test_alert_monitor_service must run successfully before this')

    notif = Notification()
    notif.email = email_config

    system_config = SystemConfigSettings()
    system_config.notifications = notif

    def email_enqueued(message, config):
        t.assertEqual(email_config.stmp_server, config.smtp_host)
        t.assertEqual(email_config.smtp_port, config.smtp_port)
        t.assertEqual(email_config.smtp_sender_email, config.smtp_login)
        t.assertEqual(email_config.smtp_sender_password, config.smtp_password)
        t.assertEqual(True, config.smtp_use_ssl)

        t.assertEqual(message['To'], email_config.email)
        t.assertEqual(message['From'], email_config.smtp_sender_email)

    mock_queue = MockEmailQueue()
    mock_queue.add_listener(email_enqueued)
    mock_config_mgr = MockSystemConfigManager(system_config)
    template = Template('Email template')
    email_notificator = AlertEmailNotifier(mock_queue, mock_config_mgr, template)
    await email_notificator.handle_alert(ALERT_MODEL)


def run_tests(args = {}):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_alert_monitor_service())
    loop.run_until_complete(test_email_notification())

test_list = [run_tests]

if __name__ == '__main__':
    Log.init('test', '.')
    run_tests()
