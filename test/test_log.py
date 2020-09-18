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

import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from cortx.utils.log import Log

def init(args):
    pass

def test1_1(args={}):
    Log.init('csm_agent', log_path="/tmp")
    Log.debug('test1_1: hello world')
    Log.info('test1_1: hello world')
    Log.audit_log("test1_1: audit log ")

def test1_2(args={}):
    Log.init('csm_setup', log_path="/tmp", level="INFO")
    Log.debug('test1_2: hello world')
    Log.info('test1_2: hello world')

def test1_3(args={}):
    Log.init('csm_cli', log_path="/tmp", level="INFO")
    Log.debug('test1_3: hello world')
    Log.info('test1_3: hello world')

test_list = [ test1_1, test1_2, test1_3]
