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

from csm.common.services import Service, ApplicationService
from cortx.utils.iem_framework import EventMessage
from typing import Optional, Iterable, Dict


class IemAppService(ApplicationService):
    """
    provides iem send interface
    """
    def __init__(self, source: str, component: str):
        self.source = source
        self.component = component
        EventMessage.init(component, source)

    def send(self, module: str, event_id: int, severity: str, message_blob: str, problem_site_id: int, \
        problem_rack_id: int, problem_node_id: int, event_time: float):
        """sends IEM 
        Args:
            module (str): A number that indicates sub module of a component that generated IEM. i.e SSPL submodule like HPI.
            event_id (int): id for event
            severity (str): The degree of impact an event has on the operation of a component. i.e A, X, E, W 
            message_blob (str): Message can be anything like string or JSON encoded message, etc
            problem_site_id (int): id of data center site.
            problem_rack_id (int): id of rack
            problem_node_id (int): id of node 
            event_time (float): event time stamp
        """
        
        EventMessage.send(module=module, event_id=event_id, severity=severity, message_blob=message_blob, problem_site_id=problem_site_id, problem_rack_id=problem_rack_id, problem_node_id=problem_node_id, event_time=event_time) 


