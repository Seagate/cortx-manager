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

import argparse
from typing import List


class Options:
    """
    A quick-and-dirty implementation that stores CSM runtime options and properties.
    """

    debug = False
    start = False
    daemonize = False
    conf_store = False

    @classmethod
    def parse(cls, args: List[str]) -> None:
        parser = argparse.ArgumentParser(description='')
        parser.add_argument('start', help='Start CSM Agent')
        parser.add_argument('-c', '--config', help='Confstore URL eg:<type>://<path>')
        parser.add_argument('--debug', help='Start CSM Agent in Debug mode',
                            action='store_true',
                            default=False)
        parser.add_argument('--daemonize', help='Start CSM Agent in Demonize mode',
                            action='store_true',
                            default=False)
        opts = vars(parser.parse_args())
        cls.debug = opts["debug"]
        cls.start = opts['start'] == 'start'
        cls.daemonize = opts['daemonize']
        cls.config = opts['config']