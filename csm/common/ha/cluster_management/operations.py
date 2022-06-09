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
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from abc import ABC, abstractmethod
from marshmallow import Schema, fields, validate
from csm.core.blogic import const
from csm.common.errors import InvalidRequest, CsmInternalError, CsmServiceNotAvailable
from cortx.utils.log import Log
from cortx.utils.conf_store.conf_store import Conf


class Operation(ABC):
    """
    Base class that will be extended by all operation implementations.

    Extending classes will have to provide implementation for
    validate_arguments and execute methods.
    The process method will call validate_arguments and execute methods in order.
    """

    not_blank_validator = validate.Length(min=1, error=const.ARG_BLANK_ERR_MSG)

    def process(self, cluster_manager, **kwargs):
        """
        Process operation.

        :param cluster_manager: cluster manager object.
        :returns: None.
        """
        self.validate_arguments(**kwargs)

        executor = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(executor, partial(self.execute, cluster_manager, **kwargs))

    @abstractmethod
    def validate_arguments(self, **kwargs):
        """Abstract method for arguments validation."""
        pass

    @abstractmethod
    def execute(self, cluster_manager, **kwargs):
        """Abstract method for execution."""
        pass

    @staticmethod
    def parse_errors(errors):
        """
        Parse the errors raised in validate_arguments method by the extending classes.

        :param errors: list of errors to parse.
        :raises InvalidRequest: after processing error messages with a concatenated result.
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
    """Cluster start operation."""

    def validate_arguments(self, **kwargs):
        """Validate arguments stub."""
        pass

    def execute(self, cluster_manager, **kwargs):
        """Execute stub."""
        pass


class ClusterStopOperation(Operation):
    """Cluster stop operation."""

    def validate_arguments(self, **kwargs):
        """Validate arguments stub."""
        pass

    def execute(self, cluster_manager, **kwargs):
        """Execute stub."""
        pass


class ClusterShutdownSignal(Operation):
    """Cluster shutdown signal operation."""

    def validate_arguments(self, **kwargs):
        """Validate arguments stub."""
        pass

    def send_kafka_message(self, msg_bus_obj, message):
        Log.debug("Sending kafka message")
        try:
            msg_bus_obj.send([str(message)])
            return True
        except Exception as e:
            Log.error(f"Error while sending message: {e}")
            return False

    def execute(self, cluster_manager, **kwargs):
        """Execute stub."""
        msg_bus_obj = kwargs.get(const.ARG_MSG_OBJ, "")
        message = {"start_cluster_shutdown": 1}
        MAX_RETRY_COUNT = Conf.get(const.CSM_GLOBAL_INDEX, const.MAX_RETRY_COUNT)
        RETRY_SLEEP_DURATION = Conf.get(const.CSM_GLOBAL_INDEX, const.RETRY_SLEEP_DURATION)

        if msg_bus_obj is None:
            Log.error("Message bus object is None")
            raise CsmServiceNotAvailable()

        is_success = False
        for retry in range(0, MAX_RETRY_COUNT):
            is_success = self.send_kafka_message(msg_bus_obj, message)
            if is_success:
                Log.debug("Message is successfully send")
                break
            Log.error(f"Failed to initialized message bus in attempt ({retry})")
            time.sleep(RETRY_SLEEP_DURATION)
        if not is_success:
            Log.error("Message bus Service not available")
            raise CsmServiceNotAvailable()


class NodeStartOperation(Operation):
    """Process start operation on node with he arguments provided."""

    def validate_arguments(self, **kwargs):
        """Validate arguments implementation for the Node start."""
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(required=True,
                                              validate=self.not_blank_validator)
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        Operation.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        """Execute implementation for the node start."""
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
    """Process stop operation on node with he arguments provided."""

    def validate_arguments(self, **kwargs):
        """Validate arguments implementation for the Node stop."""
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(
                required=True, validate=self.not_blank_validator),
            const.ARG_FORCE: fields.Bool()
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        Operation.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        """Execute implementation for the Node stop."""
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
    """Process poweroff operation on node with he arguments provided."""

    def validate_arguments(self, **kwargs):
        """Validate arguments implementation for the Node power off."""
        fields_to_validate = {
            const.ARG_RESOURCE_ID: fields.Str(
                required=True, validate=self.not_blank_validator),
            const.ARG_FORCE: fields.Bool(),
            const.ARG_STORAGE_OFF: fields.Bool()
        }
        ValidatorSchema = Schema.from_dict(fields_to_validate)
        errors = ValidatorSchema().validate(kwargs)
        Operation.parse_errors(errors)

    def execute(self, cluster_manager, **kwargs):
        """Execute implementation for the Node power off."""
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
