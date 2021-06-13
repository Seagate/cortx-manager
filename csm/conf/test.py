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

from csm.common.process import SimpleProcess
from csm.conf.setup import Setup, CsmSetupError
from cortx.utils.log import Log
from csm.core.blogic import const
from importlib import import_module
from csm.core.providers.providers import Response
from csm.common.errors import CSM_OPERATION_SUCESSFUL, CSM_FAILURE
from cortx.utils.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.validator.error import VError
from cortx.utils.validator.v_network import NetworkV
from cortx.utils.validator.v_pkg import PkgV
from argparse import Namespace


class Test(Setup):
    def __init__(self):
        super(Test, self).__init__()
        Log.info("Executing Test Cases for CSM.")

    async def execute(self, command):
        """
        Execute CSM setup test Command
        """
        try:
            Log.info("Loading Url into conf store.")
            Conf.load(const.CONSUMER_INDEX, command.options.get(
                const.CONFIG_URL))
        except KvError as e:
            Log.error(f"Configuration Loading Failed {e}")
            raise CsmSetupError("Could Not Load Url Provided in Kv Store.")

        self._validate_csm_gui_test_rpm()
        self._execute_test_plans(command)

        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _prepare_and_validate_confstore_keys(self):
        self.conf_store_keys.update({
            const.KEY_SERVER_NODE_INFO:f"{const.SERVER_NODE_INFO}",
            const.KEY_HOSTNAME:f"{const.SERVER_NODE_INFO}>{const.HOSTNAME}",
            const.KEY_CLUSTER_ID:f"{const.SERVER_NODE_INFO}>{const.CLUSTER_ID}"
            })
        try:
            Setup._validate_conf_store_keys(const.CONSUMER_INDEX, keylist = list(self.conf_store_keys.values()))
        except VError as ve:
            Log.error(f"Key not found in Conf Store: {ve}")
            raise CsmSetupError(f"Key not found in Conf Store: {ve}")

    def _fetch_mgmnt_ip(self):
        cluster_id = Conf.get(const.CONSUMER_INDEX, self.conf_store_keys[const.KEY_CLUSTER_ID])
        virtual_host_key = f"{const.CLUSTER}>{cluster_id}>{const.NETWORK}>{const.MANAGEMENT}>{const.VIRTUAL_HOST}"
        self._validate_conf_store_keys(const.CONSUMER_INDEX,[virtual_host_key])
        virtual_host = Conf.get(const.CONSUMER_INDEX, virtual_host_key)
        Log.debug(f"Validating connectivity for virtual_host:{virtual_host}")
        try:
            NetworkV().validate('connectivity', [virtual_host])
        except Exception as e:
            Log.error(f"Network Validation failed. {e}")
            raise CsmSetupError("Network Validation failed.")
        return virtual_host

    def _validate_csm_gui_test_rpm(self):
        try:
            Log.info("Validating cortx-csm_test rpm")
            PkgV().validate("rpms", ["cortx-csm_test"])
        except VError as ve:
            Log.error(f"Failed at package Validation: {ve}")
            raise CsmSetupError(f"Failed at package Validation: {ve}")

    def _execute_test_plans(self, command):
        test_plan = command.options.get("plan", "")
        Log.info(f"Executing test plan: {test_plan}")
        if test_plan == "sanity_service":
            plan_file = command.options.get("t", "")
            args_loc = command.options.get("f", "")
            log_path = command.options.get("l", "")
            output_file = command.options.get("o", "")
            if plan_file == "":
                plan_file = const.DEFAULT_TEST_PLAN
            if args_loc == "":
                args_loc = const.DEFAULT_ARG_PATH
            if log_path == "":
                log_path = const.CSM_SETUP_LOG_DIR
            if output_file == "":
                output_file = const.DEFAULT_OUTPUTFILE
            cmd = (f"/usr/bin/csm_test -t  {plan_file} -f {args_loc} -l {log_path}"
                    f" -o {output_file}")
            proc = SimpleProcess(cmd)
            _output, _err, _return_code = proc.run()
            if _return_code != 0:
                raise CsmSetupError(f"CSM Test Failed \n Output : {_output} \n "
                                    f"Error {_err} \n Return Code {_return_code}")
        else:
            self._prepare_and_validate_confstore_keys()
            management_ip = self._fetch_mgmnt_ip()
            import_obj = import_module("csm.csm_test.csm_test")
            csm_gui_test = import_obj.CsmGuiTest(const.DEFAULT_LOGFILE)
            args = Namespace(browser=const.DEFAULT_BROWSER,
                            csm_pass=const.DEFAULT_PASSWORD,
                            csm_url=f'https://{management_ip}/#/',
                            csm_user=const.DEFAULT_USERNAME,
                            headless='True',
                            test_tags=test_plan)
            Log.info(f"CSM Gui Test Arguments: {args}")
            test_status, test_output, test_log, test_report =  csm_gui_test.run_cmd_test(args)
            msg = (f"test_status:{test_status} \n "
                    f"test_output:{test_output} \n "
                    f"test_log:{test_log} \n "
                    f"test_report:{test_report} \n "
                    f"csm_gui_test.log:{const.DEFAULT_LOGFILE} \n ")
            if test_status == "FAIL":
                Log.error(msg)
                raise CsmSetupError(f"CSM Test Failed \n {msg}")
            Log.info(msg)