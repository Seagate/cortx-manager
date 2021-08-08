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

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from abc import ABC, abstractmethod

from marshmallow import Schema, fields

from csm.core.blogic import const
from csm.common.errors import InvalidRequest
from cortx.utils.log import Log


class Operation(ABC):

    def process(self, cluster_manager, **kwargs):
        self.validate_arguments(**kwargs)

        executor = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()

        loop.run_in_executor(executor, partial(self.execute, cluster_manager, **kwargs))

    @abstractmethod
    def validate_arguments(self, **kwargs):
        pass

    @abstractmethod
    def execute(self, cluster_manager, **kwargs):
        pass

    def parse_errors(self, errors):
        error_messages = []
        for each_key in errors.keys():
            error_messages.append(f"{each_key}: {''.join(errors[each_key])}")

        if len(error_messages) > 0:
            raise InvalidRequest('\n'.join(error_messages))


class ClusterStartOperation(Operation):

    def validate_arguments(self, **kwargs):
        pass

    def execute(self, cluster_manager, **kwargs):
        pass


class ClusterStopOperation(Operation):

    def validate_arguments(self, **kwargs):
        pass

    def execute(self, cluster_manager, **kwargs):
        pass


class NodeStartOperation(Operation):

    def validate_arguments(self, **kwargs):
        pass

    def execute(self, cluster_manager, **kwargs):
        pass


class NodeStopOperation(Operation):

    def validate_arguments(self, **kwargs):
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(required=True),
            const.ARG_CHECK_CLUSTER: fields.Bool()
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        self.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        node_id = kwargs.get(const.ARG_RESOURCE_ID, "")
        args = {
            "check_cluster": kwargs.get(const.ARG_CHECK_CLUSTER, True)
        }
        Log.debug(f"NodeStopOperation on node with id {node_id} and args: {args}")
        # try:
        #     operation_result = cluster_manager.node_controller.stop(node_id, args)
        #     Log.debug(f"NodePoweroffOperation result: {operation_result}")
        # except Exception as e:
        #     err_msg = f"{const.CLUSTER_OPERATIONS_ERR_MSG} : {e}"
        #     Log.error(err_msg)


class NodePoweroffOperation(Operation):

    def validate_arguments(self, **kwargs):
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(required=True),
            const.ARG_CHECK_CLUSTER: fields.Bool(),
            const.ARG_STORAGE_OFF: fields.Bool()
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        self.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        node_id = kwargs.get(const.ARG_RESOURCE_ID, "")
        args = {
            const.ARG_CHECK_CLUSTER: kwargs.get(const.ARG_CHECK_CLUSTER, True),
            const.ARG_POWER_OFF: True,
            const.ARG_STORAGE_OFF: kwargs.get(const.ARG_STORAGE_OFF, False)
        }
        Log.debug(f"NodePoweroffOperation on node with id {node_id} and args: {args}")
        # try:
        #     operation_result = cluster_manager.node_controller.stop(node_id, args)
        #     Log.debug(f"NodePoweroffOperation result: {operation_result}")
        # except Exception as e:
        #     err_msg = f"{const.CLUSTER_OPERATIONS_ERR_MSG} : {e}"
        #     Log.error(err_msg)

