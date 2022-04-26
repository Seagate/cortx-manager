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
from marshmallow import Schema, fields, validate
from csm.core.blogic import const
from csm.common.errors import InvalidRequest, CsmInternalError
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.event_framework.health import HealthEvent, HealthAttr

class Operation(ABC):
    """
    Base class that will be extended by all operation implementations.
    Extending classes will have to provide implementation for
    validate_arguments and execute methods.
    The process method will call validate_arguments and execute methods in order.
    """
    not_blank_validator = validate.Length(min=1, error=const.ARG_BLANK_ERR_MSG)

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
        """
        Parse the errors raised in validate_arguments method by
        the extending classes.
        """
        error_messages = []
        for each_key in errors.keys():
            if errors[each_key][0] == const.UNKNOWN_FIELD_ERR_MSG:
                error_messages.append(f"{each_key}: {const.ARG_NOT_SUPPORTED_ERR_MSG}")
            else:
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


class ClusterShutdownSignal(Operation):

    def validate_arguments(self, **kwargs):
        pass

    def execute(self, cluster_manager, **kwargs):
        mssg_bus_obj = kwargs.get(const.ARG_MSG_OBJ, "")
        message = {"start_cluster_shutdown": 1}
        try:
            mssg_bus_obj.send([str(message)])
        except Exception as e:
            Log.error(f"Error while sending shutdown signal:{e}")
            raise CsmInternalError(f"Error while sending shutdown signal:{e}")

class NodeStartOperation(Operation):
    """
    Process start operation on node with he arguments provided.
    """
    def validate_arguments(self, **kwargs):
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(required=True,
                                    validate=self.not_blank_validator)
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        self.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        node_id = kwargs.get(const.ARG_RESOURCE_ID, "")
        args = {
            const.ARG_POWER_ON: True
        }
        Log.debug(f"NodeStartOperation on node with id {node_id} and args: {args}")
        try:
            operation_result = cluster_manager.node_controller.start(node_id, **args)
            Log.debug(f"NodeStartOperation result: {operation_result}")
        except Exception as e:
            err_msg = f"{const.CLUSTER_OPERATIONS_ERR_MSG} : {e}"
            Log.error(err_msg)


class NodeStopOperation(Operation):
    """
    Process stop operation on node with he arguments provided.
    """
    def validate_arguments(self, **kwargs):
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(required=True,
                                    validate=self.not_blank_validator),
            const.ARG_FORCE: fields.Bool()
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        self.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        node_id = kwargs.get(const.ARG_RESOURCE_ID, "")
        args = {
            const.ARG_CHECK_CLUSTER: not kwargs.get(const.ARG_FORCE, False)
        }
        Log.debug(f"NodeStopOperation on node with id {node_id} and args: {args}")
        try:
            operation_result = cluster_manager.node_controller.stop(node_id, -1, **args)
            Log.debug(f"NodeStopOperation result: {operation_result}")
        except Exception as e:
            err_msg = f"{const.CLUSTER_OPERATIONS_ERR_MSG} : {e}"
            Log.error(err_msg)


class NodePoweroffOperation(Operation):
    """
    Process poweroff operation on node with he arguments provided.
    """
    def validate_arguments(self, **kwargs):
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(required=True,
                                    validate=self.not_blank_validator),
            const.ARG_FORCE: fields.Bool(),
            const.ARG_STORAGE_OFF: fields.Bool()
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        self.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        node_id = kwargs.get(const.ARG_RESOURCE_ID, "")
        args = {
            const.ARG_CHECK_CLUSTER: not kwargs.get(const.ARG_FORCE, False),
            const.ARG_POWER_OFF: True,
            const.ARG_STORAGE_OFF: kwargs.get(const.ARG_STORAGE_OFF, False)
        }
        Log.debug(f"NodePoweroffOperation on node with id {node_id} and args: {args}")
        try:
            operation_result = cluster_manager.node_controller.stop(node_id, -1, **args)
            Log.debug(f"NodePoweroffOperation result: {operation_result}")
        except Exception as e:
            err_msg = f"{const.CLUSTER_OPERATIONS_ERR_MSG} : {e}"
            Log.error(err_msg)

class NodeMarkFailure(Operation):
    """
    Process mark node failure request.
    """
    def validate_arguments(self, **kwargs):
        arguments = kwargs.get('arguments', "")
        num_node_id = int(Conf.get(const.CSM_GLOBAL_INDEX, const.NUM_NODE_ID))
        for id in range(num_node_id):
            valid_node_id = Conf.get(const.CSM_GLOBAL_INDEX, f"{const.KEY_NODE_ID}[{id}]")
            if arguments['id'] == valid_node_id:
                return
        raise InvalidRequest('Request body is missing or invalid request body.')

    def _create_payload(self, **kwargs):
        cluster_id = Conf.get(const.CSM_GLOBAL_INDEX, const.KEY_CLUSTERID)
        arguments = kwargs.get('arguments', "")
        node_id = arguments['id']
        health_attrs = {
            f'{HealthAttr.SOURCE}': 'csm',
            f'{HealthAttr.CLUSTER_ID}': cluster_id ,
            f'{HealthAttr.SITE_ID}': const.NOT_DEFINED,
            f'{HealthAttr.RACK_ID}': const.NOT_DEFINED,
            f'{HealthAttr.STORAGESET_ID}': const.NOT_DEFINED,
            f'{HealthAttr.NODE_ID}': node_id,
            f'{HealthAttr.RESOURCE_TYPE}':const.NODE,
            f'{HealthAttr.RESOURCE_ID}': node_id,
            f'{HealthAttr.RESOURCE_STATUS}': 'failed',
            f'{HealthAttr.SPECIFIC_INFO}': ''
            }
        return HealthEvent(**health_attrs).json

    def execute(self, cluster_manager, **kwargs):
        self.validate_arguments(**kwargs)
        mssg_bus_obj = kwargs.get(const.ARG_MSG_OBJ, "")
        payload = self._create_payload(**kwargs)
        try:
            mssg_bus_obj.send([str(payload)])
        except Exception as e:
            Log.error(f"Error while sending Mark node failure signal:{e}")
            raise CsmInternalError(f"Error while sending Mark Node failure signal:{e}")