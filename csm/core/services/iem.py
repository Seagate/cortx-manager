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

from typing import NamedTuple

from csm.common.services import ApplicationService
from cortx.utils.iem_framework import EventMessage
from cortx.utils.iem_framework.error import EventMessageError
from cortx.utils.log import Log

class IemPayload(NamedTuple):
    severity: str
    module: str
    event_id: int
    message_blob: str

class IemAppService(ApplicationService):
    """
    Provides producer and consumer operations on IEMs
    """
    severity_levels = {
        'INFO' : 'I',
        'WARN' : 'W',
        'ERROR' : 'E',
        'CRITICAL' : 'X',
        'ALERT' : 'A',
        'NOTICE' : 'N',
        'CONFIG' : 'C',
        'DETAIL' : 'D',
        'DEBUG' : 'B'
    }

    modules = {
        'SSL_EXPIRY': 'SSL'
    }

    def __init__(self):
        super().__init__()

    @staticmethod
    def init(source: str = 'S', component: str = 'CSM'):
        Log.info(f"Intializing IEM service - Component: {component}, Source: {source}")
        try:
            EventMessage.init(component, source)
        except EventMessageError as iemerror:
            Log.error(f"Event Message Initialization Error : {iemerror}")

    @staticmethod
    def send(payload: IemPayload):
        Log.info("Sending IEM : {payload}")
        try:
            # Message BLOB format is not defined yet. Using string as the data type.
            EventMessage.send(module=payload.module, event_id=payload.event_id, severity=payload.severity, \
                message_blob=payload.message_blob)
        except EventMessageError as iemerror:
            Log.error(f"Error in sending IEM. Payload : {payload}. {iemerror}")
