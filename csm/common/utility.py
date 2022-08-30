# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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

import time
from cortx.utils.conf_store import Conf
from cortx.utils.validator.error import VError
from csm.core.blogic import const
from cortx.utils.log import Log
from cortx.utils.validator.v_consul import ConsulV
from csm.common.service_urls import ServiceUrls
from cortx.utils.kv_store.error import KvError

class Utility:
    """
    Helper class for common independent utilities.
    """

    @staticmethod
    def remove_json_key(payload, key):
        """
        Removes a particular key from complex a deserialized json payload.

        Args:
            payload (dict): payload from which particular key should be deleted.
            key (str): key which is to be deleted.

        Returns:
            Modified payload.
        """
        if isinstance(payload, dict):
            return {k: Utility.remove_json_key(v, key) for k, v in payload.items() if k != key}
        elif isinstance(payload, list):
            return [Utility.remove_json_key(element, key) for element in payload]
        else:
            return payload

    @staticmethod
    def is_consul_backend(conf):
        """
        Check if backend for config is consul or not
        Args:
            conf (str): config path for configurations
        Returns:
            Boolean value
        """
        result = False
        if const.CONSUL in str(conf):
            result = True
        return result

    @staticmethod
    def get_consul_config():
        """
       Get consul endpoint related details
        """
        secret =  Conf.get(const.CONSUMER_INDEX, const.CONSUL_SECRET_KEY)
        protocol, host, port, consul_endpoint = '','','',''
        count_endpoints : str = Conf.get(const.CONSUMER_INDEX,
            const.CONSUL_NUM_ENDPOINTS_KEY)
        try:
            count_endpoints = int(count_endpoints)
        except ValueError as e:
            raise e
        for count in range(count_endpoints):
            endpoint = Conf.get(const.CONSUMER_INDEX,
                f'{const.CONSUL_ENDPOINTS_KEY}[{count}]')
            if endpoint:
                protocol, host, port = ServiceUrls.parse_url(endpoint)
                if protocol == "https" or protocol == "http":
                    consul_endpoint = endpoint
                    Log.info(f"Fetching consul endpoint : {consul_endpoint}")
                    break
        return protocol, host, port, secret, consul_endpoint

    @staticmethod
    def validate_consul():
        """
        Validate consul service
        """
        _, consul_host, consul_port, _, _ = Utility.get_consul_config()
        for retry in range(0, const.MAX_RETRY):
            try:
                Log.info(f"Connecting to consul retry count : {retry}")
                ConsulV().validate_service_status(consul_host,consul_port)
                break
            except VError as e:
                    Log.error(f"Failed to connect with consul: {e}")
                    if retry == const.MAX_RETRY-1:
                        raise e
                    time.sleep(const.SLEEP_DURATION)

    @staticmethod
    def load_csm_config_indices(conf):
        Log.info("Loading CSM configuration")
        for retry in range(0, const.MAX_RETRY):
            try:
                Conf.load(const.CONSUMER_INDEX, conf)
                break
            except KvError as e:
                if retry == const.MAX_RETRY-1:
                        raise e
                Log.error(f"Unable to fetch the configuration: {e}")
                time.sleep(const.SLEEP_DURATION)
        _, consul_host, consul_port, _, _ = Utility.get_consul_config()
        if consul_host and consul_port:
            try:
                if  not Utility.is_consul_backend(conf):
                    Utility.validate_consul()
                Conf.load(const.CSM_GLOBAL_INDEX,
                    f"consul://{consul_host}:{consul_port}/{const.CSM_CONF_BASE}")
                Conf.load(const.DATABASE_INDEX,
                    f"consul://{consul_host}:{consul_port}/{const.DATABASE_CONF_BASE}")
            except (VError, KvError) as e:
                Log.error(f"Unable to fetch the configurations from consul: {e}")
                raise e
