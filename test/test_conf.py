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
from csm.common.conf import Conf
from csm.core.blogic import const

def init(args):
    pass

def test1(args={}):
    val = Conf.get(const.CSM_GLOBAL_INDEX, 'dummy', 'default')
    return True if val == 'default' else False

def test2(args={}):
    val = Conf.get(const.INVENTORY_FILE, const.DEFAULT_INVENTORY_FILE)
    return True if val == '/etc/csm/cluster.yaml' else False

test_list = [ test1, test2 ]
