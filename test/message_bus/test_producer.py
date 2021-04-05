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

def test_send(args):
    ret = False
    message_bus = MessageBusComm()
    if message_bus:
        message_bus.init(type='producer', producer_id='test_1', message_type='test-1', method='sync')
        messages = []
        for i in range(0, 10):
            messages.append("This is test message number : " + str(i))
        message_bus.send(messages)
        ret = True
    else:
        ret = False
    return ret

test_list = [test_send]
