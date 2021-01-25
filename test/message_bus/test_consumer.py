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
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from csm.common.comm import MessageBusComm

def init(args):
    pass

def callback_fn(message):
    print(f"Message received: {message}")

def test_recv(args={}):
    ret = False
    try:
        message_bus = MessageBusComm()
        if message_bus:
            message_bus.init(type='consumer', consumer_id='csm',
                    consumer_group='test_group', consumer_message_types=["test-1"],
                    auto_ack=False, offset="earliest")
            while True:
                try:
                    message_bus.recv(callback_fn)
                except AttributeError as ex:
                    break
        else:
            ret = False
    except Exception as ex:
        ret = False
    return ret

test_list = [test_recv]
