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

import json
import os
import time
from csm.common.errors import CsmError
from cortx.utils.log import Log
from csm.common.payload import Payload, Json, JsonMessage, Dict
from csm.common.plugin import CsmPlugin
from csm.core.blogic import const
from marshmallow import Schema, fields, ValidationError
from datetime import datetime
import uuid
from cortx.utils.conf_store.conf_store import Conf
from csm.common.comm import MessageBusComm

class HealthPlugin(CsmPlugin):
    """
    Health Plugin is responsible for listening and sending on the comm channel.
    It has a callback which is called to send the received response to health
    service.. 
    Note, Health Plugin needs to be called in thread context as it blocks while
    listening for the response.
    """

    def __init__(self):
        super().__init__()
        try:
            self.health_callback = None
        except Exception as e:
            Log.exception(e)

    def init(self, **kwargs):
        pass

    def process_request(self, **kwargs):
        pass
