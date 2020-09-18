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

import sys
from csm.common.errors import CsmError, CsmNotFoundError
from cortx.utils.log import Log
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
from csm.common.queries import SortBy, QueryLimits, DateTimeRange
from typing import Optional, Iterable
import json
import threading
import errno

from schematics.models import Model
from schematics.types import IntType, StringType, DateType, BooleanType\
, DateTimeType, ListType, DictType, ModelType

from csm.core.blogic.models import CsmModel
from .comments import CommentModel


# This is an example of how Alert model can look like
class AlertModel(CsmModel):

    """
    Alert model example
    """

    _id = "alert_uuid"  # reference to another Alert model field to consider it as primary key
    alert_uuid = StringType()
    status = StringType()
    #TODO
    """
    1. Currently we are not consuming alert_type so keeping the
    placeholder for now.
    2. alert_type should be derived from SSPL message's
    info.resource_type field
    3. Once a requirement comes for consuming alert_type, we should
    make use of info.resource_type and derive the alert type.
    type = StringType()
    """
    enclosure_id = IntType()
    module_name = StringType()
    description = StringType()
    health = StringType()
    health_recommendation = StringType()
    location = StringType()
    resolved = BooleanType()
    acknowledged = BooleanType()
    severity = StringType()
    state = StringType()
    extended_info = StringType()  # May be a Nested object
    module_type = StringType()
    updated_time = DateTimeType()
    created_time = DateTimeType()
    sensor_info = StringType()
    comments = ListType(ModelType(CommentModel))
    event_details = StringType()
    name = StringType()
    serial_number = StringType()
    volume_group = StringType()
    volume_size = StringType()
    volume_total_size = StringType()
    version = StringType()
    disk_slot = IntType()
    durable_id = StringType()
    host_id = StringType()
    source = StringType()
    component = StringType()
    module = StringType()
    node_id = StringType()
    support_message = StringType()
    resource_id = StringType()

    def to_primitive(self) -> dict:
        obj = super().to_primitive()

        if self.updated_time:
            obj["updated_time"] =\
                    int(self.updated_time.replace(tzinfo=timezone.utc).timestamp())
        if self.created_time:
            obj["created_time"] =\
                    int(self.created_time.replace(tzinfo=timezone.utc).timestamp())
        return obj

    def to_primitive_filter_empty(self) -> dict:
        obj = self.to_primitive()
        obj_filtered = {key: value for key, value in obj.items() if value is not None}
        return obj_filtered

    def __hash__(self):
        return hash(self.alert_uuid)

class AlertsHistoryModel(AlertModel, CsmModel):
    """
    Alerts history model.
    Created a new separate model inherited from AlertModel and CsmModel.
    This is done because Generic DB can't decide which collection it
    should use during store-method.
    """
    _id = "alert_uuid"
    alert_uuid = StringType()

# TODO: probably, it makes more sense to put alert data directly into the fields of
# the class, rather than storing Alert as a dictionary in the _data field
class Alert(object):
    """
    Represents an alert to be sent to front end
    """

    def __init__(self, data):
        self._key = data.get("alert_uuid", None)
        self._data = data
        self._published = False
        self._timestamp = datetime.utcnow()
        self._resolved = False

    def key(self):
        return self._key

    def data(self):
        return self._data

    def timestamp(self):
        return self._timestamp

    def store(self, key):
        self._key = key
        self._data["alert_uuid"] = key

    def is_stored(self):
        return self._key is not None

    def publish(self):
        self._published = True

    def is_published(self):
        return self._published

    def resolved(self, value):
        self._resolved = value

    def is_resolved(self):
        return self._resolved


# TODO: Consider a more generic approach to storage interfaces
class IAlertStorage(ABC):
    """
    Interface for Alerts repository
    """
    @abstractmethod
    async def store(self, alert: AlertModel):
        """
        Store an alert.
        It is supposed that the passed object already has the unique key

        :param alert: Alert object
        :return: nothing
        """
        pass

    @abstractmethod
    async def retrieve(self, alert_id, def_val=None) -> Optional[AlertModel]:
        """
        Retrieves an alert by its unique key.

        :return: an Alert object or None if there is no such entity
        """
        pass

    @abstractmethod
    async def update(self, alert: AlertModel):
        """
        Saves the alert object

        :param alert: Alert object
        :return: nothing
        """
        pass

    @abstractmethod
    async def retrieve_by_range(
            self, time_range: DateTimeRange, sort: Optional[SortBy],
            limits: Optional[QueryLimits]) -> Iterable[AlertModel]:
        """
        Retrieves alerts that occured within the specified time range

        :param time_range: Alerts will be filered according to this parameter.
        :param sort: Alserts will be ordered according to this parameter
        :param limits: Allows to specify offset and limit for the query
        :return: a list of Alert objects
        """
        pass

    @abstractmethod
    async def count_by_range(self, time_range: DateTimeRange) -> int:
        """
        Retrieves the number of alerts that occurred within the specified time range

        :param time_range: Alerts will be filtered according to this parameter.
        :return: the number of suitable alerts
        """
        pass

    @abstractmethod
    async def retrieve_all(self) -> list:
        """
        Retrieves all the
        """
        pass
